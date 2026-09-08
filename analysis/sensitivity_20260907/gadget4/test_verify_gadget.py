import json,unittest
import numpy as np
from verify_gadget import paired_nonvelocity,initial_checks

class VerifyTests(unittest.TestCase):
    def example(self):
        ic={'ParticleIDs':np.array([1],dtype=np.uint64),'Coordinates':np.array([[.15625,.15625,.15625]]),
            'Masses':np.array([(20/64)**3]),'InternalEnergy':np.array([1.5]),'Velocities':np.array([[2.581988897471611,0,0]])}
        a={k:v.astype(np.uint32 if k=='ParticleIDs' else np.float32) for k,v in ic.items()}
        a.update(Density=np.array([1],np.float32),Pressure=np.array([1],np.float32))
        return a,ic
    def test_report_is_json_serializable(self):
        a,ic=self.example();json.dumps(initial_checks(a,ic,{}),allow_nan=False)
    def test_ic_velocity_error_rejected(self):
        a,ic=self.example();a['Velocities'][0,0]+=.01
        with self.assertRaises(ValueError):initial_checks(a,ic,{})
    def test_nonvelocity_difference_rejected(self):
        a,ic=self.example();b={k:v.copy() for k,v in a.items()};b['Density'][0]=2
        with self.assertRaises(ValueError):paired_nonvelocity(a,b)
    def test_velocity_only_difference_allowed(self):
        a,ic=self.example();b={k:v.copy() for k,v in a.items()};b['Velocities'][0,0]=0;paired_nonvelocity(a,b)

if __name__=='__main__':unittest.main()
