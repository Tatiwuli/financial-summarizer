
import re 
line_text = "grg rgijri  Question and Answers jeig and ogi answer "

patterns = ["Questions and Answers", "Question And Answer",
            "Question and Answer", "Questions & Answers", "Question & Answer"]
for pattern in patterns:
    print("pattern: ", pattern)
    result = re.search(re.escape(pattern), line_text)
    print("result: ", result)
    if result:
        
        print(f"Found {pattern} at line {result.start()}")







  