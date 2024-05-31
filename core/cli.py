import sys
import click
from rich.console import Console
from rich.syntax import Syntax
from rich.markdown import Markdown
from claude import Claude
import tempfile
import os
from time import sleep
from pprint import pprint as pr
import pyperclip
from llm_utils import Prompt

console = Console()


@click.group()
def cli():
    pass


@cli.command()
@click.argument("prompt", type=str)
@click.option(
    "--clipboard",
    "-c",
    is_flag=True,
    help="Copy the code from the clipboard and use it as the context",
)
@click.option(
    "--model",
    "-m",
    default="anthropic.claude-3-haiku-20240307-v1:0",
    type=str,
    help="The model to use for generation",
)
def gen(prompt, clipboard, model):
    api = Claude(model)
    system_prompt = (
        "Return the code output in <code> xml tags and \n"
        "return the explanation in <explanation> xml \n"
        "tag. Do not return anything else\n"
    )
    context = ""
    if clipboard:
        context = pyperclip.paste()
        system_prompt = (
            "Use the snippet in <context> xml tags for reference to \n"
            "answer the user request. Return the code output in \n"
            "<code> xml tags and return the explanation in <explanation> \n"
            "xml tag. You can use more than one <code> tag if necessary. \n"
            "Do not return anything else. "
            "\n\n<context>\n{context}\n</context>"
        )
    prompt_obj = Prompt(prompt, system_prompt)
    prompt_obj.set_kwargs(context=context)
    result = api.invoke(prompt_obj)

    parsed_objects = result["parsed_objects"]
    code = parsed_objects.get("code", "")
    explanation = parsed_objects.get("explanation", "")

    console.print("[bold]Input Prompt:[/bold]", prompt)
    console.print()

    console.print("[bold]Code:[/bold]")
    console.print(Syntax(code, "python", theme="nord", line_numbers=False))
    console.print()

    console.print("[bold]Explanation:[/bold]")
    console.print(Markdown(explanation))
    console.print()


@cli.command("edit-file")
@click.option(
    "--filename", "-f", default=[], multiple=True, type=str, help="File to edit"
)
@click.option(
    "--model",
    "-m",
    default="anthropic.claude-3-haiku-20240307-v1:0",
    type=str,
    help="The model to use for generation",
)
def edit_file(filename, model):
    api = Claude(model)
    system_prompt = (
        "Return the updated code enclosed within <code> xml tags. Use the files \n"
        "in <context> xml tag for reference. Each file is sperated by <file> xml tag. The \n"
        "filepath is mentioned right above the <file> xml tag. \n"
        "Provide explanation in <explanation> xml tag.  \n"
        "Do not return anything else. The output should be in the following format: \n"
        "<code> \n"
        "</code> \n"
        "<explanation> \n"
        "</explanation> \n---------\n"
    )
    context = ""
    for fname in filename:
        with open(fname, "r") as file:
            content = file.read()
            context += f"filepath: {fname}\n<file>\n{content}\n</file>\n"
    system_prompt += f"\n <context>\n{context}\n</context>"

    with tempfile.NamedTemporaryFile(mode="w", delete=True) as temp_file:
        modified_time = os.path.getmtime(temp_file.name)

        click.echo(f"Opening {temp_file.name} for editing...")
        os.popen(f"code {temp_file.name}")

        while True:
            if os.path.getmtime(temp_file.name) > modified_time:
                modified_time = os.path.getmtime(temp_file.name)
                with open(temp_file.name, "r") as file:
                    prompt = file.read()
                prompt_obj = Prompt(prompt, system_prompt)
                print(prompt_obj)
                result = api.invoke(prompt_obj, tokens=2048)
                pr(result)

                parsed_objects = result["parsed_objects"]
                diff = parsed_objects.get("diff", "")
                code = parsed_objects.get("code", "")
                explanation = parsed_objects.get("explanation", "")

                console.print("[bold]Input Prompt:[/bold]", prompt)
                console.print()

                console.print("[bold]Diff:[/bold]")
                console.print(Markdown(f"\n```diff\n{diff}\n```\n"))
                console.print()

                console.print("[bold]Code:[/bold]")
                console.print(Syntax(code, "python", theme="nord", line_numbers=False))
                console.print()

                console.print("[bold]Explanation:[/bold]")
                console.print(Markdown(explanation))
                console.print()
            try:
                sleep(1)
            except KeyboardInterrupt:
                click.echo("Exiting...")
                sys.exit(0)


if __name__ == "__main__":
    cli()
