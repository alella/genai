import re
import json
import os
import time
import boto3
from datetime import datetime as dt
from botocore.exceptions import ClientError
import xml.etree.ElementTree as ET
from rich.logging import RichHandler
from rich.console import Console
import logging
from llm_utils import Prompt


def setup_logging():

    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Set up the logger
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s][%(asctime)s][%(module)s|%(funcName)s] %(message)s",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=True,
            ),
            logging.FileHandler(
                os.path.join(logs_dir, f"{dt.now().strftime('%Y-%m-%d')}.log")
            ),
        ],
    )

    return logging.getLogger(__name__)


logger = setup_logging()


class Claude:
    def __init__(self, model_id, client=None):
        """
        :param client: A low-level client representing Amazon Bedrock Runtime.
                       Describes the API operations for running inference using Bedrock models.
                       Default: None
        """
        self.client = client
        self.model_id = model_id
        self.session_cost = 0
        self.model_costs = {
            "anthropic.claude-3-sonnet-20240229-v1:0": {
                "input_cost": 0.003 * 0.001,
                "output_cost": 0.015 * 0.001,
            },
            "anthropic.claude-3-haiku-20240307-v1:0": {
                "input_cost": 0.00025 * 0.001,
                "output_cost": 0.00125 * 0.001,
            },
        }
        self.costs_file = "costs.json"

    def _read_costs_from_disk(self):
        costs_file = "costs.json"
        if os.path.exists(costs_file):
            with open(self.costs_file, "r") as file:
                data = json.load(file)
        else:
            data = {}
        return data

    def _write_costs_to_disk(self, data):
        with open(self.costs_file, "w") as file:
            json.dump(data, file, indent=4)

    def _calc_cost(self, input_tokens, output_tokens):
        cost = (
            input_tokens * self.model_costs[self.model_id]["input_cost"]
            + output_tokens * self.model_costs[self.model_id]["output_cost"]
        )
        self.session_cost += cost
        cost = round(cost, 6)

        today = str(dt.today().date())
        data = self._read_costs_from_disk()
        data[today] = data.get(today, 0) + cost
        self._write_costs_to_disk(data)

        return cost

    def invoke_claude_3_with_text(self, prompt, system_prompt="", tokens=1024):
        """
        Invokes Anthropic Claude 3 Sonnet to run an inference using the input
        provided in the request body.

        :param prompt: The prompt that you want Claude 3 to complete.
        :return: Inference response from the model.
        """

        # Initialize the Amazon Bedrock runtime client
        client = self.client or boto3.client(
            service_name="bedrock-runtime", region_name="us-west-2"
        )

        # Invoke Claude 3 with the text prompt
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ]
        try:
            response = client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": tokens,
                        "messages": messages,
                        "system": system_prompt,
                    }
                ),
            )

            # Process and print the response
            result = json.loads(response.get("body").read())
            input_tokens = result["usage"]["input_tokens"]
            output_tokens = result["usage"]["output_tokens"]
            output_list = result.get("content", [])
            content = ""
            for i, output_item in enumerate(output_list):
                content = output_item["text"]
                break
            objs = self._xml_to_json(content)
            output = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "user_prompt": prompt,
                "system_prompt": prompt,
                "max_output_tokens": tokens,
                "parsed_objects": objs,
                "raw_content": content,
                "cost": self._calc_cost(input_tokens, output_tokens),
                "cost_str": f"{self._calc_cost(input_tokens, output_tokens)} USD",
                "session_cost": self.session_cost,
            }

            return output

        except ClientError as err:
            logger.error(
                "Couldn't invoke Claude 3 Sonnet. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise

    def _xml_to_json(self, input_str):
        def _xml_to_dict(element):
            if len(element) == 0:  # if the element has no children
                return element.text
            return {child.tag: _xml_to_dict(child) for child in element}

        data = {
            tag: text.strip()
            for tag, text in re.findall(r"<(\w+)>(.*?)<\/\1>", input_str, re.DOTALL)
        }
        if "tool_invoke" in data:
            root = ET.fromstring("<x>" + data["tool_invoke"] + "</x>")
            data["tool_invoke"] = _xml_to_dict(root)
        return data

    def invoke(self, prompt_instance, tokens=1024, write_file_name=""):
        response = self.invoke_claude_3_with_text(
            prompt_instance.get_user_prompt(),
            prompt_instance.get_system_prompt(),
            tokens,
        )
        markdown = "# Answer\n\n"
        markdown += response["raw_content"]
        markdown += "\n\n"
        if response["parsed_objects"]:
            markdown += "# Parsed Objects\n\n```json\n"
            markdown += json.dumps(response["parsed_objects"], indent=2, sort_keys=True)
            markdown += "\n```\n\n"
        markdown += "# Metadata\n\n```json\n"
        metadata = {
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "cost": f"{response['cost_str']} USD",
            "session_cost": f"{response['session_cost']} USD",
        }
        markdown += json.dumps(metadata, indent=2)
        markdown += "\n```\n\n-----\n"

        if write_file_name:
            with open(write_file_name, "w") as w:
                w.write(markdown)
        response_dir = os.path.join(os.path.dirname(__file__), "responses")
        os.makedirs(response_dir, exist_ok=True)
        file_path = os.path.join(response_dir, f"{dt.today()}.md")
        with open(file_path, "w") as w:
            w.write(markdown)
        return response


def main():
    wrapper = Claude("anthropic.claude-3-haiku-20240307-v1:0")
    previous_timestamp = None
    logger.info(f"Starting claude")

    while True:
        # Get the current timestamp of the input.txt file
        current_timestamp = os.path.getmtime("input.txt")

        # Check if the timestamp has changed
        if previous_timestamp != current_timestamp:
            # Read the text prompt from the file
            with open("input.txt", "r") as f:
                text_prompt = f.read()
            logger.info(f"Invoking claude")
            prompt_instance = Prompt(text_prompt, "")
            wrapper.invoke(prompt_instance, write_file_name="output.md")

            # Update the previous timestamp
            previous_timestamp = current_timestamp

        # Wait for 1 second before checking the file again
        time.sleep(1)


if __name__ == "__main__":
    main()
