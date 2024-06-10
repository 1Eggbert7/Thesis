# conditions.py
# Alexander Leszczynski
# 08-06-2024

import py_trees
from openai import OpenAI
from prompts import PRE_PROMPT_AMBIGUOUS, PRE_PROMPT_KNOWN, PRE_PROMPT_KNOWN_2, PRE_PROMPT_AMBIGUOUS2, PRE_PROMPT_CHECK_MAPPING
from config import MAX_LLM_CALL, LLM
import state
import json

client = OpenAI()

class CheckForAmbiguity(py_trees.behaviour.Behaviour):
    """
    This is the condition to check if the user input is ambiguous.
    """
    # Condition to check if the user input is ambiguous
    def __init__(self, name, conversation):
        super(CheckForAmbiguity, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            # Call the LLM to check for ambiguity
            response = self.check_ambiguity_with_llm(self.conversation)
            print("Is it Ambiguous?: ", response)
            if response == "True":
                return py_trees.common.Status.SUCCESS
        elif 'ambig' in self.conversation[-1]['content']:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE

    def check_ambiguity_with_llm(self, conversation):
        """
        This function checks if the user input is ambiguous using the Chatgpt 3.5 turbo model.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "False"
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)

        try:
            # Construct the final prompt by inserting the user input#
            if len(conversation) == 1:
                predefined_messages_ambiguous = [
                        {"role": "system", "content": PRE_PROMPT_AMBIGUOUS},
                    ]
            else:
                predefined_messages_ambiguous = [
                        {"role": "system", "content": PRE_PROMPT_AMBIGUOUS2},
                    ]
            messages = predefined_messages_ambiguous + conversation  # Start with the predefined context.
            #print("Messages: ", messages)

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
        
class CheckForNewSeq(py_trees.behaviour.Behaviour):
    counter = 0  # Class attribute to count the total calls across instances

    def __init__(self, name, conversation):
        super(CheckForNewSeq, self).__init__(name)
        self.conversation = conversation

    def update(self):
        # later i will have an api call to openai here that checks if the input_string requests a new sequence
        CheckForNewSeq.counter += 1  # Increment the counter each time the behavior is called
        if 'New Seq' in self.conversation[-1]['content']:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE
    
class CheckVarKnownCondition(py_trees.behaviour.Behaviour):
    """
    This condition checks if var_known is True.
    """

    def __init__(self, name):
        super(CheckVarKnownCondition, self).__init__(name)

    def update(self):
        if state.var_known:
            #print("var_known is True")
            return py_trees.common.Status.SUCCESS
        #print("var_known is False")
        return py_trees.common.Status.FAILURE

# replied: "Great choice! I'll prepare some delicious pancakes with maple syrup and berries for you. Just sit back and enjoy!" instead of 'True'
"""
User:  Hey I'm hungry.
Is it Ambiguous?:  True
Assistant:  Hello! I can definitely help with that. What specific dish would you like me to prepare for you?
User: I don't know, do you have any suggestions?
Is it Ambiguous?:  True
Assistant:  Of course! Here are a few options for you to choose from:
1. Full English breakfast
2. Avocado toast with sausage on the side
3. Pancakes with maple syrup and berries

Please let me know if any of these options appeal to you, or if you have any other preferences!
User: Number 3 sounds yummy, I want that
Is it Ambiguous?:  False
Is it Known?:  Great choice! I'll prepare some delicious pancakes with maple syrup and berries for you. Just sit back and enjoy!
Eggbert3
"""
class CheckForKnown(py_trees.behaviour.Behaviour):
    """
    This condition checks if the user input is known.
    """

    def __init__(self, name, conversation):
        super(CheckForKnown, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            # Call the LLM to check if the user input is known
            response = self.check_known_with_llm(self.conversation)
            print("Is it Known?: ", response)
            if response == "True":
                return py_trees.common.Status.SUCCESS
        
        elif 'known' in self.conversation[-1]['content']:
            print("Is it Known?: True")
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE
    
    def check_known_with_llm(self, conversation):
        """
        This function checks if the user input is known using the Chatgpt 3.5 turbo model.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "False"
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)

        try:
            # Construct the final prompt by inserting the user input
            if len(conversation) == 1:
                predefined_messages_known = [
                    {"role": "system", "content": PRE_PROMPT_KNOWN},
                ]
            else:
                predefined_messages_known = [
                        {"role": "system", "content": PRE_PROMPT_KNOWN_2},
                    ]
            messages = predefined_messages_known + conversation  # Start with the predefined context.
            #print("The conversation before the LLM call: ", conversation)
            #print("Messages for Known: ", messages)

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
        
class CheckVarKnowNo(py_trees.behaviour.Behaviour):
    """
    This condition checks if var_KnowNo only contains one action. If this is false then it contains more than one action. 0 is not possible.
    """

    def __init__(self, name):
        super(CheckVarKnowNo, self).__init__(name)

    def update(self):
        if len(state.var_KnowNo) == 1:
            #print("var_KnowNo has only one action", state.var_KnowNo)
            return py_trees.common.Status.SUCCESS
        #print("var_KnowNo has more than one action", state.var_KnowNo)
        return py_trees.common.Status.FAILURE

class CheckMapping(py_trees.behaviour.Behaviour):
    """
    This condition checks if the user input maps to the action in var_KnowNo.
    """

    def __init__(self, name, conversation):
        super(CheckMapping, self).__init__(name)
        self.conversation = conversation

    def update(self):
        if LLM:
            # Call the LLM to check if the user input maps to the action in var_KnowNo
            response = self.check_mapping_with_llm(self.conversation)
            print("Does it map to the action in var_KnowNo?: ", response)
            if response == "True":
                return py_trees.common.Status.SUCCESS
        elif 'map' in self.conversation[-1]['content']:
            return py_trees.common.Status.SUCCESS
        return py_trees.common.Status.FAILURE

    def check_mapping_with_llm(self, conversation):
        """
        This function checks if the user input actually maps to the action in var_KnowNo using the Chatgpt 3.5 turbo model.
        """
        # This logic is to prevent the LLM from being called too many times
        if state.var_total_llm_calls >= MAX_LLM_CALL:
            print("Exceeded the maximum number of LLM calls.")
            return "False"
        state.var_total_llm_calls += 1
        #print("number of total llm calls was raised to: ", state.var_total_llm_calls)

        try:
            # Construct the final prompt by inserting the user input
            formatted_conversation = self.format_conversation(conversation)
            predefined_messages = [
                    {"role": "system", "content": PRE_PROMPT_CHECK_MAPPING.format(state.var_KnowNo[0], state.var_KnowNo[0], formatted_conversation)},
                ]
            messages = predefined_messages # Start with the predefined context.
            #print("PRE_PROMPT_CHECK_MAPPING: ", PRE_PROMPT_CHECK_MAPPING.format(state.var_KnowNo[0], state.var_KnowNo[0], formatted_conversation))
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
        
    def format_conversation(self, conversation):
        """
        This function formats the conversation to be used in the LLM call.
        """
        # The format should be User: <user_input> Assistant: <assistant_response> User: <user_input> ...
        formatted_conversation = ""
        for i, message in enumerate(conversation):
            if i % 2 == 0:
                formatted_conversation += f"User: {message['content']}\n"
            else:
                formatted_conversation += f"Assistant: {message['content']}\n"
        return formatted_conversation
    
class CheckVarInf(py_trees.behaviour.Behaviour):
    """
    This condition checks if var_inf is True.
    """

    def __init__(self, name):
        super(CheckVarInf, self).__init__(name)

    def update(self):
        if state.var_inf:
            #print("var_inf is True")
            return py_trees.common.Status.SUCCESS
        #print("var_inf is False")
        return py_trees.common.Status.FAILURE

class CheckNewSeq(py_trees.behaviour.Behaviour):
    """
    This action checks the new sequence generated by the LLM. The sequence is in the var_generated_sequence variable.
    """

    def __init__(self, name):
        super(CheckNewSeq, self).__init__(name)

    def update(self):
        #self.logger.debug("%s [CheckNewSeq::update()]" % self.name) # this is a debugtool to see the name of the action

        sequence = state.var_generated_sequence
        if not sequence:
            self.logger.error("The generated sequence is empty.")
            return py_trees.common.Status.FAILURE

        format_check, format_message = self.check_sequence_format(sequence)
        if not format_check:
            self.logger.error(format_message)
            return py_trees.common.Status.FAILURE
        else:
            self.logger.debug(format_message)
        
        functions = self.load_json('functions.json')
        ingredients = self.load_json('ingredients.json')
        functions_check, functions_message = self.check_functions_exist(sequence, functions, ingredients)
        if not functions_check:
            functions_message = "The sequence contains errors. Please check the following:\n" + "\n".join(state.var_found_errors_in_sequence)
            self.logger.error(functions_message)
            return py_trees.common.Status.FAILURE

        return py_trees.common.Status.SUCCESS

    def load_json(self, filepath):
        """
        This function loads a JSON file.
        """
        with open(filepath, 'r') as file:
            return json.load(file)

    # can be improved
    def check_sequence_format(self, sequence):
        """
        This function checks the format of the sequence generated by the LLM.
        """
        if not sequence or not isinstance(sequence, dict):
            return False, "The sequence is empty or not properly formatted."
        
        for step in sequence["sequence"]:
            
            if "step" not in step:
                state.var_found_errors_in_sequence.append("Each step must contain 'step' and 'action' fields. 'step' is missing.")
            if "action" not in step:
                state.var_found_errors_in_sequence.append("Each step must contain 'step' and 'action' fields. 'action' is missing.")
            if state.var_found_errors_in_sequence:
                return False, "The sequence contains errors. Please check the following:\n" + "\n".join(state.var_found_errors_in_sequence)
            if not isinstance(step["step"], str):
                state.var_found_errors_in_sequence.append("Step number must be a string.")
            if not isinstance(step["action"], str):
                state.var_found_errors_in_sequence.append("Action must be a string.")
            if state.var_found_errors_in_sequence:
                return False, "The sequence contains errors. Please check the following:\n" + "\n".join(state.var_found_errors_in_sequence)                
        
        return True, "Sequence format is valid."

    def check_functions_exist(self, sequence, functions, ingredients):
        """
        This function checks if the functions in the sequence exist in the functions list. It also checks if the parameters are of the correct type and exist in the ingredients list.
        """
        # Iterate through the sequence steps
        for step in sequence["sequence"]:
            action = step["action"]
            func_name = action.split("(")[0]
            #print("func_name: ", func_name)
            
            # Extract parameters from action
            params = action[action.find("(") + 1 : action.find(")")].split(",")
            params = [p.strip() for p in params if p.strip()]

            function_found = False
            for full_func_name in functions["functions"].keys():
                # Check if the function name matches the start of the full function name (including parameter signature) in one of the functions
                if full_func_name.startswith(func_name + "("):
                    #print("found the function that matches the action", full_func_name, func_name)
                    function_found = True
                    func_signature = full_func_name
                    expected_params = func_signature[func_signature.find("(") + 1 : func_signature.find(")")].split(",")
                    expected_params = [p.strip() for p in expected_params if p.strip()]
                    i = 0 
                    #print("params and expected_params: ", params, expected_params)
                    if len(params) != len(expected_params):
                        error_message = f"Function '{func_signature}' expects {len(expected_params)} parameters, but {len(params), params} were provided."
                        state.var_found_errors_in_sequence.append(error_message)
                    elif len(params) == 0:
                        self.logger.debug(f"Function '{func_signature}' has no parameters.")
                    else:
                        for expected_param in expected_params:
                            # for each parameter, check if the type of the parameter matches the expected type
                            match expected_param:
                                case "number":
                                    if not params[i].isnumeric():
                                        #print(f"param {i, params[i]} is not a number") # return error
                                        error_message = f"Function '{func_signature}' expects parameter {i} to be a number, but '{params[i]}' was provided."
                                        state.var_found_errors_in_sequence.append(error_message) 
                                    else: 
                                        self.logger.debug(f"param {i, params[i]} is a number")     
                                case "item":
                                    if params[i] not in ingredients["ingredients"]:
                                        #print(f"param {i, params[i]} is not an item of ingredients") # return error
                                        error_message = f"Function '{func_signature}' expects parameter {i} to be an item, but '{params[i]}' was provided."
                                        state.var_found_errors_in_sequence.append(error_message)
                                    else:
                                        self.logger.debug(f"param {i, params[i]} is an item of ingredients")
                                case "sandwich_item":
                                    if params[i] not in ["avocado_toast", "jelly_toast", "peanut_butter_toast", "toasted_bread"]:
                                        #print(f"param {i, params[i]} is not an item of sandwich_items")
                                        error_message = f"Function '{func_signature}' expects parameter {i} to be a bread item, but '{params[i]}' was provided."
                                        state.var_found_errors_in_sequence.append(error_message)
                                    else:
                                        self.logger.debug(f"param {i, params[i]} is an item of sandwich_items")
                                case "toasted_bread":
                                    if params[i] not in ["toasted_bread"]:
                                        #print(f"param {i, params[i]} is not an item of toasted_bread")
                                        error_message = f"Function '{func_signature}' expects parameter {i} to be toasted bread, but '{params[i]}' was provided."
                                        state.var_found_errors_in_sequence.append(error_message)
                                    else:
                                        self.logger.debug(f"param {i, params[i]} is a toasted_bread")
                                case _:
                                    #print(f"Function '{func_signature}' has an unexpected parameter signature.")
                                    error_message = f"Function '{func_signature}' has an unexpected parameter signature."
                                    state.var_found_errors_in_sequence.append(error_message)
                            i += 1

                        break
            
            if not function_found:
                #print(f"Function '{func_name}' does not exist in the functions list.")
                error_message = f"Function '{func_name}' does not exist in the functions list."
                state.var_found_errors_in_sequence.append(error_message)
            
        if state.var_found_errors_in_sequence:
                return False, "Errors were found in the sequence."
        return True, "All functions exist in the functions list."
