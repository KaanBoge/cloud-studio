"""Generate documented planned inputs, never alter running cases."""
from run_flash import ROOT,input_for,save,budget

def main():
    dest=ROOT/'planned_inputs';dest.mkdir(exist_ok=False);rows=[]
    for level in (3,4,5):
        for mode in (0,1):
            p=dest/f"L{level}_chi100_{'tanh13' if mode else 'sharp13'}.par"
            p.write_text(input_for(level,mode));rows.append(dict(level=level,mode=mode,input=str(p),
                full_pair_budget_gib=2*budget(level)/1024**3,status='Planned input, not proof of execution'))
    save(ROOT/'planned_inputs.json',rows)

if __name__=='__main__':main()
