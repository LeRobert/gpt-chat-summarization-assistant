import openai
import tiktoken


def num_tokens_in_string(text: str, encoding_name: str = "cl100k_base") -> int:
    """Returns a number of GPT tokens in a text string.
    param: text: string
    param: encoding_name: string (default: "cl100k_base", which is encoding for gpt-4 and gpt-3.5)
    return: int (number of tokens)
    """
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(text))
    return num_tokens


def openai_completion(prompt: list[dict], llm_model: str, random_value: float = 0.8) -> str:
    """
    OpenAI text completion API call.
    param: prompt: string
    param: random_value: float
    return: string (completion or error message)
    """
    print("Sending to OpenAI API - prompt for completion:\n", prompt)
    try:
        response = openai.ChatCompletion.create(
            model=llm_model,
            messages=prompt,
            temperature=random_value,
        )
    except openai.error.OpenAIError as e:
        print(f"OpenAI API returned an API error: {e}")
        raise
    else:
        return response['choices'][0]['message']['content']


def openai_image(prompt: str) -> str:
    """
    OpenAI image generation API call. Current model is DALL-E 2
    param: prompt: string
    return: image_url: string
    """
    print("Sending to OpenAI API - prompt for image:\n", prompt)
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="512x512"
        )
        image_url = response['data'][0]['url']
    except openai.error.OpenAIError as e:
        print(f"OpenAI API returned an API error: {e}")
        raise
    else:
        print(image_url)
        return image_url
