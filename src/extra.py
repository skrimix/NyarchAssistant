from __future__ import absolute_import
import importlib, subprocess
import re, base64, io
import os, sys
import xml.dom.minidom, html
import importlib, subprocess, functools


def rgb_to_hex(r, g, b):
    """
    Convert RGB values from float to hex.

    Args:
        r (float): Red value between 0 and 1.
        g (float): Green value between 0 and 1.
        b (float): Blue value between 0 and 1.

    Returns:
        str: Hex representation of the RGB values.
    """
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))

def human_readable_size(size: float, decimal_places:int =2) -> str:
    size = int(size)
    unit = ''
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024.0 or unit == 'PiB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def extract_expressions(text, expressions_list):
    expressions = []
    current_expression = None
    current_text = ""

    tokens = text.split()
    i = 0
    while i < len(tokens):
        if tokens[i].startswith("(") and tokens[i].endswith(")"):
            expression = tokens[i][1:-1]
            if expression in expressions_list:
                if current_text.strip():
                    expressions.append({"expression": current_expression, "text": current_text.strip()})
                    current_text = ""
                current_expression = expression
            else:
                current_text += tokens[i] + " "
        else:
            if current_expression is None:
                current_text += tokens[i] + " "
            else:
                current_text += tokens[i] + " "
        i += 1

    if current_text.strip():
        if current_expression:
            expressions.append({"expression": current_expression, "text": current_text.strip()})
        else:
            expressions.append({"expression": None, "text": current_text.strip()})

    return expressions

class ReplaceHelper:
    DISTRO = None
    AVATAR_HANDLER = None

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
    def set_handler(handler):
        ReplaceHelper.AVATAR_HANDLER = handler

    @staticmethod
    def get_expressions() -> str:
        if ReplaceHelper.AVATAR_HANDLER is None:
            return ""
        result = ""
        for expression in ReplaceHelper.AVATAR_HANDLER.get_expressions():
            result += " (" + expression + ")"
        return result

    @staticmethod
    def get_desktop_environment() -> str:
        desktop = os.getenv("XDG_CURRENT_DESKTOP")
        if desktop is None:
            desktop = "Unknown"
        return desktop

def get_spawn_command() -> list:
    """
    Get the spawn command to run commands on the user system

    Returns:
        list: space diveded command  
    """
    if is_flatpak():
        return ["flatpak-spawn", "--host"]
    else:
        return []
def get_image_base64(image_str: str):
    """
    Get image string as base64 string, starting with data:/image/jpeg;base64,

    Args:
        image_str: content of the image codeblock 

    Returns:
       base64 encoded image 
    """
    if not image_str.startswith("data:image/jpeg;base64,"):
        image = encode_image_base64(image_str)
        return image
    else:
        return image_str

def get_image_path(image_str: str):
    """
    Get image string as image path

    Args:
        image_str: content of the image codeblock 

    Returns:
       image path 
    """
    if image_str.startswith("data:image/jpeg;base64,"):
        raw_data = base64.b64decode(image_str[len("data:image/jpeg;base64,"):])
        saved_image = "/tmp/" + image_str[len("data:image/jpeg;base64,"):][30:] + ".jpg"
        with open(saved_image, "wb") as f:
            f.write(raw_data)
        return saved_image
    return image_str

def convert_history_openai(history: list, prompts: list, vision_support : bool = False):
    """Converts Newelle history into OpenAI format

    Args:
        history (list): Newelle history 
        prompts (list): list of prompts 
        vision_support (bool): True if vision support

    Returns:
       history in openai format 
    """
    result = []
    if len(prompts) > 0:
        result.append({"role": "system", "content": "\n".join(prompts)})
    
    for message in history:
        if message["User"] == "Console":
            result.append({
                "role": "user",
                "content": "Console: " + message["Message"]
            })
        else:
            image, text = extract_image(message["Message"])
            if vision_support and image is not None and message["User"] == "User":
                image = get_image_base64(image)
                result.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image}
                        }
                    ],
                })
            else:
                result.append({
                    "role": "user" if message["User"] == "User" else "assistant",
                    "content": message["Message"]
                })
    print(result)
    return result

def encode_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return "data:image/jpeg;base64," + encoded_string

def extract_image(message: str) -> tuple[str | None, str]:
    """
    Extract image from message

    Args:
        message: message string

    Returns:
        tuple[str, str]: image and text, if no image, image is None 
    """
    img = None
    if message.startswith("```image"):
        img = message.split("\n")[1]
        text = message.split("\n")[3:]                    
        text = "\n".join(text)
    else:
        text = message
    return img, text

def quote_string(s):
    if "'" in s:
        return "'" + s.replace("'", "'\\''") + "'"
    else:
        return "'" + s + "'"

def replace_variables(text: str) -> str:
    """
    Replace variables in prompts
    Supported variables:
        {DIR}: current directory
        {DISTRO}: distribution name
        {DE}: desktop environment

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
    if "{EXPRESSIONS}" in text:
        text = text.replace("{EXPRESSIONS}", ReplaceHelper.get_expressions())
    return text

def markwon_to_pango(markdown_text):
    markdown_text = html.escape(markdown_text)
    initial_string = markdown_text
    # Convert bold text
    markdown_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', markdown_text)
    
    # Convert italic text
    markdown_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', markdown_text)

    # Convert monospace text
    markdown_text = re.sub(r'`(.*?)`', r'<tt>\1</tt>', markdown_text)

    # Convert strikethrough text
    markdown_text = re.sub(r'~(.*?)~', r'<span strikethrough="true">\1</span>', markdown_text)
    
    # Convert links
    markdown_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', markdown_text)
    
    # Convert headers
    absolute_sizes = ['xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large']
    markdown_text = re.sub(r'^(#+) (.*)$', lambda match: f'<span font_weight="bold" font_size="{absolute_sizes[6 - len(match.group(1)) - 1]}">{match.group(2)}</span>', markdown_text, flags=re.MULTILINE)
    
    # Check if the generated text is valid. If not just print it unformatted
    try:
        xml.dom.minidom.parseString("<html>" + markdown_text + "</html>")
    except Exception as e:
        print(markdown_text)
        print(e)
        return initial_string
    return markdown_text

def find_module(full_module_name):
    """
    Returns module object if module `full_module_name` can be imported.

    Returns None if module does not exist.

    Exception is raised if (existing) module raises exception during its import.
    """
    try:
        return importlib.import_module(full_module_name)
    except Exception as _:
        return None


def install_module(module, path):
    if find_module("pip") is None:
        print("Downloading pip...")
        subprocess.check_output(["bash", "-c", "wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py"])
    r = subprocess.run([sys.executable, "-m", "pip", "install", "--target", path, module], capture_output=False)
    return r

def is_flatpak() -> bool:
    """
    Check if we are in a flatpak

    Returns:
        bool: True if we are in a flatpak
    """
    if os.getenv("container"):
        return True
    return False

def can_escape_sandbox() -> bool:
    """
    Check if we can escape the sandbox 

    Returns:
        bool: True if we can escape the sandbox
    """
    if not is_flatpak():
        return True
    try:
        r = subprocess.check_output(["flatpak-spawn", "--host", "echo", "test"])
    except subprocess.CalledProcessError as _:
        return False
    return True

def override_prompts(override_setting, PROMPTS):
    prompt_list = {}
    for prompt in PROMPTS:
        if prompt in override_setting:
            prompt_list[prompt] = override_setting[prompt]
        else:
            prompt_list[prompt] = PROMPTS[prompt]
    return prompt_list


def force_async(fn):
    '''
    turns a sync function to async function using threads
    '''
    from concurrent.futures import ThreadPoolExecutor
    import asyncio
    pool = ThreadPoolExecutor()

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # make it awaitable

    return wrapper


def force_sync(fn):
    '''
    turn an async function to sync function
    '''
    import asyncio

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            return asyncio.get_event_loop().run_until_complete(res)
        return res

    return wrapper
