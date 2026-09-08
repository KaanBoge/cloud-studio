"""Compile actual isolated native input/mass-update fragments for synthetic tests.

This omits neighbor search, Riemann solve and MPI transport. It is NOT an evolved
native simulation or a check of thermal evolution. All generated files retained.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1')
TESTROOT = ROOT/'flux_tests_v1'
BUILD_SHA = '01457ba7a87dfc4054366d240b66f0ba8caca310af74f945eeafb6ebd928e509'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def make_harness():
    if sha(ROOT/'build_report.json') != BUILD_SHA:
        raise ValueError('Isolated build evidence changed')
    text = (ROOT/'repaired/hydro/hydro_evaluate.h').read_text()
    begin = text.index('    if(mode == 0)')
    end = text.index('    /* certain particles should never enter the loop:')
    dispatch = text[begin:end]
    start = text.index('                double dmass_holder =')
    finish = text.index('                 /* this gets subtracted here', start)
    update = text[start:finish]
    if dispatch.count('dt_hydrostep_i = local.dt_hydrostep_i;') != 1:
        raise ValueError('Missing actual source assignment')
    if 'typedef double MyFloat;' not in (ROOT/'repaired.i').read_text():
        raise ValueError('Unexpected native input timestep precision')
    harness = '''#include <math.h>
struct Input { double Mass, dt_hydrostep_i; };
#define INPUT_STRUCT_NAME Input
static struct Input supplied, DATAGET_NAME[1];
static void particle2in_hydra(struct Input *in, int target, int loop_iteration) { *in = supplied; }
void flux_probe(int mode, double flux, double step_i, double step_j,
                double mass_i, double mass_j, int active, double *answer) {
    int target=0, loop_iteration=0, j=0;
    struct Input local;
    struct {double rho;} Fluxes = {flux};
    struct {double Mass;} P[1] = {{mass_j}};
    struct {double dMass;} SphP[1] = {{0}}, out = {0};
    double dt_hydrostep_i, dt_hydrostep_j=step_j;
    double FluxCorrectionFactor_to_i=1, FluxCorrectionFactor_to_j=1;
    int j_is_active_for_fluxes=active;
    supplied=(struct Input){mass_i,step_i}; DATAGET_NAME[0]=supplied;
'''+dispatch+update+'''
    answer[0]=out.dMass; answer[1]=SphP[0].dMass;
}
'''
    TESTROOT.mkdir(exist_ok=False)
    (TESTROOT/'native_flux_fragment.c').write_text(harness)
    argv=['cc','-shared','-fPIC','-O1','-ffast-math','-Wall',
          '-Werror=uninitialized','-Werror=maybe-uninitialized',
          str(TESTROOT/'native_flux_fragment.c'),'-o',str(TESTROOT/'native_flux_fragment.so')]
    with (TESTROOT/'compile.log').open('x') as stream:
        subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=30)
    return dict(command=argv,native_source_sha256=sha(ROOT/'repaired/hydro/hydro_evaluate.h'),
                harness_sha256=sha(TESTROOT/'native_flux_fragment.c'))


class FluxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance=make_harness()
        cls.lib=ctypes.CDLL(str(TESTROOT/'native_flux_fragment.so'))
        cls.probe=cls.lib.flux_probe
        cls.probe.argtypes=[ctypes.c_int]+[ctypes.c_double]*5+[ctypes.c_int,ctypes.POINTER(ctypes.c_double)]
        cls.probe.restype=None

    def call(self,mode=0,flux=2,di=.125,dj=.25,mi=2,mj=5,active=0):
        answer=(ctypes.c_double*2)()
        self.probe(mode,flux,di,dj,mi,mj,active,answer)
        self.assertEqual(answer[0],-answer[1])
        return tuple(answer)

    def test_zero_flux_both_input_paths(self):
        for mode in (0,1):self.assertEqual(self.call(mode,flux=0),(0,0))

    def test_positive_negative_flux_both_paths(self):
        for mode in (0,1):
            self.assertEqual(self.call(mode),(.25,-.25))
            self.assertEqual(self.call(mode,flux=-1),(-.125,.125))

    def test_shorter_target_uses_supplied_step(self):
        for mode in (0,1):
            self.assertEqual(self.call(mode,di=.0625,dj=.25),(.125,-.125))

    def test_longer_target_defers_integrated_exchange(self):
        for mode in (0,1):self.assertEqual(self.call(mode,di=.25,dj=.125),(0,0))

    def test_equal_inactive_double_visit_total(self):
        for mode in (0,1):
            a=self.call(mode,di=.125,dj=.125)
            b=self.call(mode,flux=-2,di=.125,dj=.125,mi=5,mj=2)
            self.assertEqual(a,(.125,-.125))
            self.assertEqual(a[0]+b[1],.25)
            self.assertEqual(a[1]+b[0],-.25)

    def test_equal_active_single_visit_total(self):
        # Synthetic branch coverage, not a claim that this optimization is active.
        for mode in (0,1):self.assertEqual(self.call(mode,di=.125,dj=.125,active=1),(.25,-.25))

    def test_limiter_uses_donor_mass(self):
        for mode in (0,1):
            self.assertEqual(self.call(mode,flux=100),(.5,-.5))
            a=self.call(mode,flux=-100)
            self.assertAlmostEqual(a[0],-.2,places=15)

    def test_zero_target_step(self):
        for mode in (0,1):self.assertEqual(self.call(mode,di=0),(0,0))

    def test_source_is_only_declared_assignment(self):
        old=(ROOT/'reference/hydro/hydro_evaluate.h').read_text()
        new=(ROOT/'repaired/hydro/hydro_evaluate.h').read_text()
        marker='    /* certain particles should never enter the loop: check for these */'
        self.assertEqual(new,old.replace(marker,'    dt_hydrostep_i = local.dt_hydrostep_i;\n\n'+marker))


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FluxTests))
    report=dict(status='passed_synthetic_fragments_not_native_evolution' if result.wasSuccessful() else 'failed',
                tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                build_report_sha256=BUILD_SHA,script_sha256=sha(__file__),
                provenance=getattr(FluxTests,'provenance',None),native_simulations_started=0,
                limitations='Actual input dispatch and mass-update fragments only; no neighbor/Riemann/MPI/thermal-evolution proof.')
    with (ROOT/'flux_test_report.json').open('x') as stream:json.dump(report,stream,indent=2)
    raise SystemExit(0 if result.wasSuccessful() else 1)
