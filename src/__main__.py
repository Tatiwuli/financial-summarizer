import json
from src.services.precheck import PrecheckError  , run_precheck 

if __name__ == "__main__":


    try:
        payload = run_precheck()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except PrecheckError as e:
        print(json.dumps(
            {"error": {"message": e.message}}, ensure_ascii=False))
        raise SystemExit(1)
