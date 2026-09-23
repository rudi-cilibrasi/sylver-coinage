"""Trusted episode worker. Always launched under the process-tree accountant."""
from pathlib import Path
import sys
import traceback

from .agent import run_agent
from .common import read, write
from .exact import batch
from .policies import run_policy
from .proof import canonical_proof, verify, verifier_profile
from .protocol import Client, Session
from .snapshot import validate_bundle


def main():
    cfg=read(sys.argv[1]);out=Path(cfg['output'])
    bundle=read(cfg['bundle']);validate_bundle(bundle)
    if bundle['manifest']['verifier']!=verifier_profile():raise ValueError('verifier version mismatch')
    try:
        if cfg['phase']=='discovery':
            session=Session(bundle,cfg['binary'],out,cfg['limits'],cfg.get('policy',{}).get('proof_style','compact'),
                            read(cfg['resume_nodes']) if cfg.get('resume_nodes') else None)
            if 'agent' in cfg:run_agent(Client(session),cfg['agent'],out,cfg['seed'])
            elif 'script' in cfg:
                for request in cfg['script']:
                    session.request(request)
            else:run_policy(Client(session),cfg['policy'],cfg['seed'])
            write(out/'result.json',{'status':'submitted' if session.submitted else 'unsolved'})
        else:
            proof=read(cfg['submission'])
            def exact(ps):
                if cfg.get('reference_python'):
                    from sylver.solver import solve_position
                    rows=[]
                    for p in ps:
                        value=solve_position(p)
                        rows.append({'position':list(p),'outcome':'N' if value.is_winning else 'P',
                                     'frobenius':value.frobenius,'states':value.states_evaluated})
                        write(out/'python-leaves.json',rows)
                    return rows
                return batch(cfg['binary'],ps,out/'finite-replay',cfg['limits']['wall_seconds'])
            result=verify(proof,bundle['snapshot'],bundle['manifest']['target'],exact)
            (out/'certificate.json').write_bytes(canonical_proof(proof,bundle['snapshot'])+b'\n')
            write(out/'result.json',result)
    except Exception as exc:
        write(out/'result.json',{'status':'invalid','error':str(exc)})
        raise


if __name__=='__main__':main()
