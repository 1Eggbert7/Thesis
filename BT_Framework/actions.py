# actions.py
# Alexander Leszczynski
# 10-06-2024

import py_trees
from openai import OpenAI
from prompts import PRE_PROMPT_AMBIGUOUS_ANSWER, PRE_PROMPT_KNOWN, FORMAT_SCHEME, FIRST_SHOT, SECOND_SHOT, THIRD_SHOT, PRE_PROMPT_KNOWNO, SECOND_SHOT_ASSISTANT_ANSWER, TEST_JSON_MC_RAW, PRE_PROMPT_MC_SCORES, AMBIGUOUS_SHOT, PREDEFINED_SAFETY_FEASIBILITY, PRE_PROMPT_NEW_SEQ, FIRST_SHOT_EXPLAIN_SEQ, FIRST_SHOT_EXPLAIN_SEQ_ANSWER
from config import MAX_LLM_CALL, LLM
from utils import format_conversation
import state
import json
import random
import numpy as np

client = OpenAI()

class PrintAmbiguousAnswer(py_trees.behaviour.Behaviour):

    def __init__(self, name, conversation):
        super(PrintAmbiguousAnswer, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            # Call the LLM to generate the response
            #print("the conversation before the LLM call: ", self.conversation)
            response = self.generate_ambiguous_response_with_llm(self.conversation)
            print("Assistant: ", response.replace('\\n', '\n').replace('\\\'', '\''))
            self.conversation.append({"role": "assistant", "content": response}) 
            #print("conversation with the LLM response: ", self.conversation)
        else:
            print("Ambiguous Answer 1")
        return py_trees.common.Status.SUCCESS
    
    def generate_ambiguous_response_with_llm(self, conversation):
        """
        This function generates a response to an ambiguous user input using the Chatgpt 3.5 turbo model.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)
        #print("the conversation before the LLM call: ", conversation)
        try:
            # Construct the final prompt by inserting the user input
            predefined_messages_ambiguous_answer = [
                    {"role": "system", "content": PRE_PROMPT_AMBIGUOUS_ANSWER}
                ]
            messages = predefined_messages_ambiguous_answer + conversation  # Start with the predefined context.
            #print("prepromt Messages for answering: ", messages)

            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    # response_format={ "type": "json_object" },
                    messages=messages
                    )
            
            # Extract and return the response content
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return "False"
        
class WaitForUserInput(py_trees.behaviour.Behaviour):
    """
    This action waits for new user input from the keyboard.
    """

    def __init__(self, name, process_user_input_func):
        super(WaitForUserInput, self).__init__(name)
        self.process_user_input_func = process_user_input_func

    def update(self):
        new_user_input = input("User: ")
        self.process_user_input_func(new_user_input)  # Re-trigger the behavior tree with the new input
        return py_trees.common.Status.SUCCESS

class PrintExit1(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PrintExit1, self).__init__(name)

    def update(self):
        print("Eggbert1")
        return py_trees.common.Status.SUCCESS

class PrintExit2(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PrintExit2, self).__init__(name)

    def update(self):
        print("Eggbert2")
        return py_trees.common.Status.SUCCESS
    
class PrintExit3(py_trees.behaviour.Behaviour):
    def __init__(self, name):
        super(PrintExit3, self).__init__(name)

    def update(self):
        print("Eggbert3")
        return py_trees.common.Status.SUCCESS
    
class KnowNoMapping(py_trees.behaviour.Behaviour):
    """
    This action leverages a modified version of the KnowNo-framework to fill the var_KnowNo list with possible actions that could map to the user input.
    """

    def __init__(self, name, conversation):
        super(KnowNoMapping, self).__init__(name)
        self.conversation = conversation

    def update(self):

        #create_messages_KnowNo(conversation)

        result = self.create_mc_KnowNo(self.conversation)
        #print("Result: ", result)
        the_options, the_options_list , the_add_mc_prefix = self.process_mc_raw(result, add_mc='an option not listed here')
        #print("the options: ", the_options)
        #print("the add mc prefix: ", the_add_mc_prefix)
        logprobs = self.get_logprobs(the_options, self.conversation)
        #print('\n====== Raw log probabilities for each option ======')
        #for option, logprob in logprobs.items():
        #    print(f'Option: {option} \t log prob: {logprob}')

        # next we fill the state of var_KnowNo with the options that are above a certain threshold
        self.fill_var_KnowNo(logprobs, the_options_list)

        return py_trees.common.Status.SUCCESS
    
    def fill_var_KnowNo(self, logprobs, the_options_list):
        """
        This function fills the var_KnowNo list with the options that are above a certain threshold.
        """
        qhat = 0.8
        top_tokens = list(logprobs.keys())
        top_logprobs = [logprob if logprob is not None else -1e10 for logprob in logprobs.values()]  # Replace None with a large negative number to avoid errors

        mc_smx_all = self.temperature_scaling(top_logprobs, temperature=5)
        
        # include all options with score >= 1-qhat
        prediction_set = [
            token for token_ind, token in enumerate(top_tokens)
            if mc_smx_all[token_ind] >= 1 - qhat
        ]

        # print
        #print('Softmax scores:', mc_smx_all)
        print('Prediction set:', prediction_set)

        case = {
                'A': 1,
                'B': 2,
                'C': 3,
                'D': 4,
                'E': 5
            }
        
        for token in prediction_set:
            state.var_KnowNo.append(the_options_list[case[token] - 1])
        print("var_KnowNo: ", state.var_KnowNo)

    def temperature_scaling(self, logits, temperature):
        """
        This function applies temperature scaling to the logits.
        """
        #print('Temperature scaling with T =', temperature)
        #print('Original logits:', logits)
        logits = np.array(logits)
        logits /= temperature

        # apply softmax
        logits -= logits.max()
        logits = logits - np.log(np.sum(np.exp(logits)))
        smx = np.exp(logits)
        return smx

    def create_mc_KnowNo(self, conversation):   
        """
        This function creates the multi-choice messages for the KnowNo-framework.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)


        predefined_messages_KnowNo = [
                    {"role": "system", "content": PRE_PROMPT_KNOWNO.format(FORMAT_SCHEME)},
                    {"role": "user", "content": "I want the bacon and egg sandwich."},
                    {"role": "assistant", "content": FIRST_SHOT},
                    {"role": "user", "content": "Hey, I'm hungry, what can I eat?"},
                    {"role": "assistant", "content": SECOND_SHOT_ASSISTANT_ANSWER},
                    {"role": "user", "content": "I'll have option 2."},
                    {"role": "assistant", "content": SECOND_SHOT}
                ]
        messages = predefined_messages_KnowNo + conversation # Start with the predefined context.
        # to see the messages
        #for message in messages:
        #    print(message["content"])

        try:
            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    # response_format={ "type": "json_object" },
                    messages=messages
                    )
            
            # Extract and return the response content
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return "Failed LLM call"
    
    def get_logprobs(self, options, conversation):
        """
        This function gets the logprobs for the multi-choice options.
        """
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1

        predefined_messages_mc_scores = [
                    {"role": "system", "content": PRE_PROMPT_MC_SCORES.format(options)}
                ]
        messages = predefined_messages_mc_scores + conversation # Start with the predefined context.
        

        try:
            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    logprobs=True,
                    top_logprobs=20,
                    max_tokens=1,
                    logit_bias={
                        32: 100.0,   #  A (without space at front)
                        33: 100.0,   #  B (without space at front)
                        34: 100.0,   #  C (without space at front)
                        35: 100.0,   #  D (without space at front)
                        36: 100.0,   #  E (without space at front)
                        362: 100.0,  #  A (with space at front)
                        426: 100.0,  #  B (with space at front)
                        356: 100.0,  #  C (with space at front)
                        423: 100.0,  #  D (with space at front)
                        469: 100.0   #  E (with space at front)
                    }
                    )
            
            option_logprobs = {'A': None, 'B': None, 'C': None, 'D': None, 'E': None}
            choice = completion.choices[0]

            # Access the content, which contains the logprobs details for each token
            content_logprobs = choice.logprobs.content

            # Iterate through each token's logprob in content_logprobs
            for token_logprob in content_logprobs:
                # For each token, iterate through its top_logprobs to find probabilities of interest
                for top_logprob in token_logprob.top_logprobs:
                    # Check if the current top_logprob token is one of our options (A, B, C, D, or E)
                    #print(top_logprob)
                    if top_logprob.token in option_logprobs:
                        # If this is the first time we see a logprob for this token or if this logprob is higher, update it                        
                        if option_logprobs[top_logprob.token] is None or top_logprob.logprob > option_logprobs[top_logprob.token]:
                            option_logprobs[top_logprob.token] = top_logprob.logprob

            # Convert option_logprobs to a list of log probabilities in the same order as top_tokens for consistency
            top_tokens = ['A', 'B', 'C', 'D', 'E']  # Define the order of tokens explicitly
            top_logprobs = [option_logprobs[token] if token in option_logprobs else float('-inf') for token in top_tokens]  # Use '-inf' for missing options


            # Extract and return the response content
            return option_logprobs
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return "Failed LLM call"

    def process_mc_raw(self, mc_raw, add_mc='an option not listed here'):
        """
        This function processes the raw output from the LLM for the multi-choice options.
        """
        mc_processed_all = []
        
        # Assuming mc_raw is a JSON string
        mc_gen_raw_json = json.loads(mc_raw)

        # Now mc_gen_raw_json is a dictionary, we access its 'choices' key
        for choice in mc_gen_raw_json["choices"]:
            # Combine the option and action into a single string
            option_action = f"{choice['action']}"
            # Append the combined string to the list
            mc_processed_all.append(option_action)
        if len(mc_processed_all) < 4:
            raise Exception('Cannot extract four options from the raw output.')
        
        # Check if any repeated option - use do nothing as substitue
        mc_processed_all = list(set(mc_processed_all))
        if len(mc_processed_all) < 4:
            num_need = 4 - len(mc_processed_all)
            for _ in range(num_need):
                mc_processed_all.append('do nothing')
        prefix_all = ['A) ', 'B) ', 'C) ', 'D) ']
        if add_mc is not None:
            mc_processed_all.append(add_mc)
            prefix_all.append('E) ')
        random.shuffle(mc_processed_all)

        # get full string
        mc_prompt = ''
        for mc_ind, (prefix, mc) in enumerate(zip(prefix_all, mc_processed_all)):
            mc_prompt += prefix + mc
            if mc_ind < len(mc_processed_all) - 1:
                mc_prompt += '\n'
        add_mc_prefix = prefix_all[mc_processed_all.index(add_mc)][0]
        return mc_prompt, mc_processed_all, add_mc_prefix

class ExecuteAction(py_trees.behaviour.Behaviour):
    """
    This action executes the action that maps to the user input.
    """

    def __init__(self, name, conversation):
        super(ExecuteAction, self).__init__(name)
        self.conversation = conversation

    def update(self):
        response = self.execute_action(self.conversation)
        print("Assistant: ", response)
        return py_trees.common.Status.SUCCESS

    def execute_action(self, conversation):
        """
        This function executes the action by acknowledging the user input and providing the response.
        """
        #choices =  ['bacon and egg sandwich', 'avocado toast with sausage on the side', 'peanut butter and jelly sandwich', 'vegetable stir fry with rice', 'pancakes with maple syrup and berries', 'full English breakfast', 'tortilla with tomatoes beans and egg (huevos rancheros)', 'bean and cheese quesadilla', 'grilled tomato and mushroom bruschetta', 'clean living room floor']
        #random_choice = random.choice(choices)
        response = "Great choice! I will execute the sequence for {}.".format(state.var_KnowNo[0])
        return response

class RunSafetyCheck(py_trees.behaviour.Behaviour):
    """
    This action runs a safety check to ensure that the user request for a new Sequenence is feasible and safe.
    """

    def __init__(self, name, conversation):
        super(RunSafetyCheck, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            response = self.run_safety_check(self.conversation)
            #print("Did it pass the safety check?: ", response)
        else:
            print("Safety Check 1")
            response = 'False'  # Default to 'False' if LLM is not used

        if 'true' in response.strip()[:10].lower():
            state.var_inf = False
            return py_trees.common.Status.SUCCESS
        else:
            state.var_inf = True

            # Extract the part after "Explanation:"
            if 'Explanation:' in response:
                explanation = response.split('Explanation:')[1].strip()
                state.var_decline_explanation = explanation
            return py_trees.common.Status.SUCCESS


    def run_safety_check(self, conversation):
        """
        This function runs a safety check to ensure that the action to be executed is safe, with ChatGPT 3.5 Turbo.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1
        formatted_conversation = format_conversation(conversation)
        #print("formatted conversation: ", formatted_conversation)
        predefined_messages_safety_feasibility = PREDEFINED_SAFETY_FEASIBILITY
        convo_to_add = {"role": "user", "content": formatted_conversation}
        predefined_messages_safety_feasibility.append(convo_to_add)
        messages = predefined_messages_safety_feasibility        
        try:
            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                    )
            
            # Extract and return the response content
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return "Failed LLM call"
        
class DeclineRequest(py_trees.behaviour.Behaviour):
    """
    This action declines the user request if the safety check fails.
    """

    def __init__(self, name):
        super(DeclineRequest, self).__init__(name)

    def update(self):
        print("I'm sorry, I cannot execute the action you requested. The reason is:", state.var_decline_explanation)
        return py_trees.common.Status.SUCCESS

# needs testing
class GenerateNewSequence(py_trees.behaviour.Behaviour):
    """
    This action generates a new sequence given the action is safe and feasible.
    """

    def __init__(self, name, conversation):
        super(GenerateNewSequence, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            response = self.generate_new_sequence(self.conversation)
            print("The generated sequence is: ", response)
            state.var_generated_sequence = response
        else:
            print("Generate New Sequence 1")
            response = 'False'
        return py_trees.common.Status.SUCCESS

    def generate_new_sequence(self, conversation):
        """
        This function generates a new sequence given the action is safe and feasible.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)
        try:
            # Construct the final prompt by inserting the user input
            predefined_messages_new_sequence = [
                    {"role": "system", "content": PRE_PROMPT_NEW_SEQ}
                ]
            messages = predefined_messages_new_sequence + conversation  # Start with the predefined context.
            #print("prepromt Messages for generating new sequence: ", messages)

            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    response_format={ "type": "json_object" },
                    messages=messages
                    )
            
            # Extract and return the response content
            response_content = completion.choices[0].message.content
            
            # Parse the JSON response and save it to the variable
            state.var_generated_sequence = json.loads(response_content)
            print("Generated sequence in the var: ", state.var_generated_sequence)

            # Extract and return the response content
            return response_content
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return "Failed LLM call"

# needs testing
class ExplainSequence(py_trees.behaviour.Behaviour):
    """
    This action explains the generated sequence to the user.
    """

    def __init__(self, name, conversation):
        super(ExplainSequence, self).__init__(name)
        self.conversation = conversation

    def update(self):
        #print("The sequence to explain is the generated sequence: ", state.var_generated_sequence)
        if LLM:
            response = self.explain_sequence(self.conversation)
            print("Assistant: ", response)
        else:
            print("The sequence to explain is the generated sequence: ", state.var_generated_sequence)
            print("The sequence is a very great sequence. \nIt is a very good sequence.")
            response = 'False'
        return py_trees.common.Status.SUCCESS
    
    def explain_sequence(self, conversation):
        """
        This function explains the generated sequence to the user with the ChatGPT 3.5 Turbo model.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)
        try:
            # Construct the final prompt by inserting the user input
            predefined_messages_explain_sequence = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that explains the steps a robot will take to fulfill a user's request. "
                        "The explanation should be clear and concise, focusing on the actions without adding unnecessary details. "
                        "At the end of the explanation, ask the user if the sequence sounds good to them. "
                        "Do not provide any extra information or detail about how the actions are performed beyond what is specified."
                    )
                }
            ]
            
            first_shot = {"role": "user", "content": FIRST_SHOT_EXPLAIN_SEQ}
            first_shot_answer = {"role": "assistant", "content": FIRST_SHOT_EXPLAIN_SEQ_ANSWER}
            predefined_messages_explain_sequence.append(first_shot)
            predefined_messages_explain_sequence.append(first_shot_answer)

            # Convert the sequence to a string format
            sequence_str = "\n".join([f"Step {item['step']}: {item['action']}" for item in state.var_generated_sequence_test['sequence']])

            # Format the conversation
            formated_conversation = format_conversation(conversation)

            # Append the formatted conversation and sequence to the predefined messages
            predefined_messages_explain_sequence.append(
                {
                    "role": "user",
                    "content": f"Yes, now given this conversation and the generated sequence, can you explain the sequence to me?\n{formated_conversation}\nThe sequence is:\n{sequence_str}"
                }
            )

            messages = predefined_messages_explain_sequence  # Start with the predefined context.
            #print("prepromt Messages for explaining the sequence: ", messages)
            


            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                    )
            
            # Extract and return the response content
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in LLM call: {e}")
            return "Failed LLM call"
        
class ReportFailureBackToUser(py_trees.behaviour.Behaviour):
    """
    This action reports the failure back to the user. It is triggered when the automated check of the newly generated sequence fails.
    """

    def __init__(self, name, conversation):
        super(ReportFailureBackToUser, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            #response = self.report_failure_back_to_user()
            response = "I’m sorry, but I ran into an issue while trying to create what you requested. Would you like to try again, or do you have any other questions I can help with?"
            self.conversation.append({"role": "assistant", "content": response})
            print("Assistant: ", response)
        else:
            print("The sequence failed the automated check.")
            response = 'False'

        return py_trees.common.Status.SUCCESS

    def report_failure_back_to_user(self):
        """
        This function reports the failure back to the user with the ChatGPT 3.5 Turbo model.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "I'm sorry, I cannot help you at the moment.The maximum number of LLM calls has been exceeded."
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)
        try:
            # Construct the final prompt by inserting the user input
            error_messages = "\n".join(state.var_found_errors_in_sequence)

            predefined_messages_report_failure = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that reports back to the user when the automated check of the newly generated sequence fails. "
                        "The report should be clear and concise, explaining the reason for the failure without adding unnecessary details. "
                        "At the end of the report, ask the user if they would like to try generating a new sequence or if they have any other questions. "
                        "Do not provide any extra information or detail about how the actions are performed beyond what is specified."
                        "To report the failure you have access to the error messages: '" + error_messages + "' Make sure to explain the error messages to the user in a way that is easy to understand."
                    )
                }
            ]

            messages = predefined_messages_report_failure  # Start with the predefined context.
            print("prepromt Messages for reporting failure in the sequence: ", messages)

            # Make the API call
            completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages
                    )
            
            # Extract and return the response content
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error in LLM call: {e}")





