# financial-summarizer

#User flow

!Earning call e Conferennce call tem mesmo workflow.

1. Seleciona:
    - seleciona call_type = earning ou conference
    - seleciona summary_length: short/long 
2. Upload PDF
3. (sistema) PDF processor para  validar 
    -  tamanho : se passar de 10MB, retorne invalido imediatamente.
    - extrai secoes de texto. 
        Se Q&A nao existir: invalida 
        Se Presentation nao existir: Seguir, e o LLM e pedido  para focar apenas no Q&A  summary + aviso no front

4. (sistema) Chama o workflow que contem  o q_a_summarizer ,judge_q_a_summary, write_call_overview  dos llm utils , processando os pompts de acordo com o user  input. 
5. (sistema) Envia os resultados para frontend
6. Frontend renderiza o output.

    #"[ouput_overview["title"]]"

    ##"[output_overview["executives_list"]]"

    ##"[output_overview["overview"]]"

    ##"[q_a_summary["summary"]]"


#file structure
/src

    __main__.py CLI 
    pra rodar `python -m src`

    /api
        /app: Endpoints

    /utils : Functions generalizable for other components; Pure utility functions, with no business logic knowledge  
        /pdf_processor.py: convet pdf to text, and extract q&a and presentation sections ✓

    /services: Functions that connect utilities functions with endpoints
        /precheck.py : Receive pdf and return valid/invalid response to endpoint ; Use pdf_processor  utility functions ✓
        
    /llm
        /llm_client: models setup and generate content function ✓
        /llm_utils: (all are for earning call and conference) summarize_q_a ✓, judge_q_a_summary✓, write_call_overview ✓

/config ✓
    /prompts_summarize
        /overview.json
            system_prompt: FORMAT(CALL_TYPE)
            user_prompt: FORMAT(TRANSCRIPT, Q_A_SUMMARY)
    /runtime.py: Hardocded inputs for test 

    /prompts_judge
        /q_a_summary.json

.env OPENAIAPI, GEMINIAPI 
requirements.txt

#LLM outputs
- os raw outputs sao passados entre llms 
- os outputs formatados em json com _ensure_dict eh para renderizar no frontend 
#envelope
###run_prrecheck()
 {
                "type": "precheck",
                "data": {
                    "summary_length": SUMMARY_LENGTH,
                    "qa_transcript": result.get("qa_transcript"),
                    "presentation_transcript": result.get("presentation_transcript"),
                    "pdf": {
                        "original_filename": result.get("original_filename"),
                        "uuid_filename": result.get("uuid_filename"),
                        "transcript_path": result.get("transcript_path"),
                        "presentation_text_length": pres_len,
                        "qa_text_length": qa_len
                    }
                }
            }
------------------
TODO
- retornar metrics tbm e append no blocks. Agora so apendamos o texto
-- Padronizar as mensagens de erro gerado pelopdf processor. Agora, essas mensagens sao passadas para precheck, mas hardcoded. 
- Rodar unit tests pra precheck ( deu ceto com happy path)
- Error handling pra prompt config.
- Validar se o true/false no llm judgeoutput eh booleano ou nao