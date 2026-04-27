"""
Text-to-speech utility module.
"""
import os


def text_to_speech(text):
    """
    Convert text to speech using pico2wave and aplay.
    
    Args:
        text (str): The text to convert to speech.
    """
    os.system(f'pico2wave -w output.wav "{text}" && aplay output.wav')
