import json
from src.services.precheck import PrecheckError, run_validate_file

if __name__ == "__main__":

    try:
        payload = run_validate_file()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except PrecheckError as e:
        print(json.dumps(
            {"error": {"message": e.message}}, ensure_ascii=False))
        raise SystemExit(1)
