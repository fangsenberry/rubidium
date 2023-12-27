import rubidium
from datetime import datetime

def main():
    file_check = input("input file? (y/n): ")
    
    if file_check == 'y':
        with open("questions_file.txt", "r") as f:
            all_questions = f.read()
            questions = all_questions.split(";")
            
            acruby = rubidium.ActorCriticRuby()
            for question in questions:
                question = question.strip("\n")
                # print(question)
                # return
                # Start time
                start_time = datetime.now()
                print(f"handling question: {question} at time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                acruby.net_assess(question)

                # End time
                end_time = datetime.now()

                # Calculate elapsed time in minutes
                time_elapsed = (end_time - start_time).total_seconds() / 60  # Convert to minutes
                print(f"Time elapsed: {time_elapsed:.2f} minutes")
                            
            return
    else:
        question = input("What is your question?\n")
        
    acruby = rubidium.ActorCriticRuby()
    acruby.net_assess(question)

if __name__ == '__main__':
    main()
    
'''
Context/Background that this question falls under: The role of human competence versus algorithmic decision-making in contemporary organizations, including AI's implications on the workforce. Question: How can policymakers anticipate and mitigate the risks associated with an over-reliance on algorithmic processes in critical sectors? In decreasing order of importance, what are the policies/approaches/strategies that policymakers must focus on to mitigate the risks that you have identified?

'''