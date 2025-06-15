import json
import os
from openai import OpenAI

class ScriptGenerator:
    def __init__(self, api_key=None):
        """Initialize the script generator with OpenAI API"""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
    
    def set_api_key(self, api_key):
        """Set the OpenAI API key"""
        self.api_key = api_key
        self.client = OpenAI(api_key=self.api_key)
    
    def generate_script(self, scene_description):
        """
        Generate a conversation script based on the scene description
        
        Args:
            scene_description (str): Description of the scene/situation
            
        Returns:
            dict: Generated script data with title, situation, and conversation
        """
        if not self.client:
            raise ValueError("OpenAI API key is required. Please set your API key first.")
        
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert English teacher who creates listening materials for Japanese middle school students. 
                        Create natural English conversations that are appropriate for middle school level (grades 7-9).
                        
                        Guidelines:
                        - Use simple, clear vocabulary appropriate for middle school students
                        - Include common phrases and expressions used in daily conversation
                        - Keep sentences relatively short and easy to understand
                        - Use natural conversational flow with appropriate greetings and responses
                        - Include 4-8 lines of dialogue between 2-3 speakers
                        - Make the conversation realistic and engaging for teenagers
                        
                        Respond with JSON in this exact format:
                        {
                            "title": "Short descriptive title in English",
                            "situation": "Brief description of the situation in Japanese",
                            "conversation": [
                                {"speaker": "Speaker name", "text": "English dialogue"},
                                {"speaker": "Speaker name", "text": "English dialogue"}
                            ]
                        }"""
                    },
                    {
                        "role": "user",
                        "content": f"Create a middle school level English conversation for this scene: {scene_description}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI API")
            result = json.loads(content)
            
            # Validate the response structure
            if not all(key in result for key in ["title", "situation", "conversation"]):
                raise ValueError("Invalid response structure from OpenAI API")
            
            if not isinstance(result["conversation"], list) or len(result["conversation"]) == 0:
                raise ValueError("Invalid conversation format")
            
            return result
            
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse OpenAI response: {e}")
        except Exception as e:
            raise Exception(f"Failed to generate script: {e}")
    
    def validate_script(self, script_data):
        """
        Validate the generated script data
        
        Args:
            script_data (dict): The script data to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ["title", "situation", "conversation"]
        
        if not all(field in script_data for field in required_fields):
            return False
        
        if not isinstance(script_data["conversation"], list):
            return False
        
        for line in script_data["conversation"]:
            if not isinstance(line, dict) or "speaker" not in line or "text" not in line:
                return False
        
        return True
