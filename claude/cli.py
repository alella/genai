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

console = Console()


@click.group()
def cli():
    pass


@cli.command()
@click.argument("prompt", type=str)
@click.option(
    "--model",
    "-m",
    default="anthropic.claude-3-haiku-20240307-v1:0",
    type=str,
    help="The model to use for generation",
)
def gen(prompt, model):
    api = Claude(model)
    system_prompt = "Return the code output in <code> xml tags and return the explanation in <explanation> xml tag. Do not return anything else"
    result = api.invoke(prompt, system_prompt=system_prompt)

    parsed_objects = result["parsed_objects"]
    code = parsed_objects.get("code", "")
    explanation = parsed_objects.get("explanation", "")

    console.print("[bold]Input Prompt:[/bold]", prompt)
    console.print()

    console.print("[bold]Code:[/bold]")
    console.print(Syntax(code, "python"))
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
    system_prompt = """
    Return the code changes that need to be made in markdown git diff format. Use the files
    in <context> xml tag for reference. Each file is sperated by <file> xml tag. The first
    line of the file is the filepath and not a part of the file content.
    This output should be in <diff> xml tags. Provide explanation in <explanation> xml tag. 
    Do not return anything else.
    """
    context = ""
    for fname in filename:
        print(fname)
        with open(fname, "r") as file:
            content = file.read()
        context += f"""
        <file>
        # filepath: {fname}
        {content}
        </file>
        """
    system_prompt += f"\n <context>{context}</context>"

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
        modified_time = os.path.getmtime(temp_file.name)

        click.echo(f"Opening {temp_file.name} for editing...")
        os.popen(f"code {temp_file.name}")

        while True:
            if os.path.getmtime(temp_file.name) > modified_time:
                modified_time = os.path.getmtime(temp_file.name)
                with open(temp_file.name, "r") as file:
                    prompt = file.read()
                result = api.invoke(prompt, system_prompt=system_prompt, tokens=2048)
                # click.echo(f"Result: {result}")
                pr(result)

                parsed_objects = result["parsed_objects"]
                code = parsed_objects.get("diff", "")
                explanation = parsed_objects.get("explanation", "")

                console.print("[bold]Input Prompt:[/bold]", prompt)
                console.print()

                console.print("[bold]Code:[/bold]")
                console.print(Markdown(f"\n```diff\n{code}\n```\n"))
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
