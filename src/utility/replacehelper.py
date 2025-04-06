import os 
import subprocess
from .system import get_spawn_command
import time
from .system import is_wayland 

class ReplaceHelper:
    DISTRO = None
    controller = None
    AVATAR_HANDLER = None

    @staticmethod
    def set_controller(controller):
        ReplaceHelper.controller = controller
 
    @staticmethod
    def get_distribution() -> str:
        """
        Get the distribution

        Returns:
            str: distribution name
            
        """
        if ReplaceHelper.DISTRO is None:
            try:
                ReplaceHelper.DISTRO = subprocess.check_output(get_spawn_command() + ['bash', '-c', 'lsb_release -ds']).decode('utf-8').strip()
            except subprocess.CalledProcessError:
                ReplaceHelper.DISTRO = "Unknown"
        
        return ReplaceHelper.DISTRO

    @staticmethod
    def gisplay_server() -> str:
        """
        Get the server

        Returns:
            str: server name
            
        """ 
        return "Wayland" if is_wayland() else "X11"

    @staticmethod
    def get_desktop_environment() -> str:
        desktop = os.getenv("XDG_CURRENT_DESKTOP")
        if desktop is None:
            desktop = "Unknown"
        return desktop

    @staticmethod
    def get_user() -> str:
        """
        Get the user

        Returns:
            str: user name
            
        """
        if ReplaceHelper.controller is None:
            return "User"
        return ReplaceHelper.controller.newelle_settings.username
   
    @staticmethod
    def set_handler(handler):
        ReplaceHelper.AVATAR_HANDLER = handler

    @staticmethod
    def get_expressions() -> str:
        if ReplaceHelper.AVATAR_HANDLER is None:
            return ""
        result = ""
        for expression in ReplaceHelper.AVATAR_HANDLER.get_expressions():
            if expression is not None:
                result += " (" + expression + ")"
        return result

    @staticmethod
    def get_motions() -> str:
        if ReplaceHelper.AVATAR_HANDLER is None:
            return ""
        result = ""
        for motion in ReplaceHelper.AVATAR_HANDLER.get_motions():
            if motion is not None:
                result += " (" + motion + ")"
        return result

def replace_variables(text: str) -> str:
    """
    Replace variables in prompts
    Supported variables:
        {DIR}: current directory
        {DISTRO}: distribution name
        {DE}: desktop environment
        {USER}: user's username
        {DATE}: current date

    Args:
        text: text of the prompt

    Returns:
        str: text with replaced variables
    """
    text = text.replace("{DIR}", os.getcwd())
    if "{DISTRO}" in text:
        text = text.replace("{DISTRO}", ReplaceHelper.get_distribution())
    if "{DE}" in text:
        text = text.replace("{DE}", ReplaceHelper.get_desktop_environment())
    if "{DATE}" in text:
        text = text.replace("{DATE}", str(time.strftime("%H:%M %Y-%m-%d")))
    if "{USER}" in text:
        text = text.replace("{USER}", ReplaceHelper.get_user())
    if "{DISPLAY}" in text:
        text = text.replace("{DISPLAY}", ReplaceHelper.gisplay_server())
    if "{EXPRESSIONS}" in text:
        text = text.replace("{EXPRESSIONS}", ReplaceHelper.get_expressions())
    if "{MOTIONS}" in text:
        text = text.replace("{MOTIONS}", ReplaceHelper.get_motions())
    return text
