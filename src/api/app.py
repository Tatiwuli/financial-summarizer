from fastapi import FastAPI, status 
from fastapi.responses import JSONResponse
from services.precheck import PrecheckError, run_precheck



app = FastAPI(title="Summarizer v1")

@app.get("v1/precheck")
def precheck():
    """
    Validate the pdf size and text sections with a pdf path 
    """

    try: 
        payload = run_precheck()
        return payload
    except PrecheckError as e:
        
        return JSONResponse(
            content=f'{{"error":{{"code":"{e.code}","message":"{e.message}"}}}}',
            status_code= status.HTTP_400_BAD_REQUEST,
            media_type="application/json"
        )
