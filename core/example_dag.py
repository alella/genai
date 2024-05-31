from llm_utils import llm_tool, ToolPrompt, LLMFNS
from claude import Claude
from pprint import pprint as pr
from utils import setup_logging

log = setup_logging()
api = Claude("anthropic.claude-3-haiku-20240307-v1:0")


class Node:
    def __init__(self, name, description, children=[]):
        self.name = name
        self.description = description
        self.children = children
        self.previous = []
        self.evaluated = False
        self.results = ""
        self._response = {}

    def evaluate(self):
        if self.name == "root":
            self.evaluated = True
            self.results = "none"
            return
        if all([c.evaluated for c in self.previous]):
            previous_results = "\n".join([c.results for c in self.previous])
            prompt = ToolPrompt(
                f'use context to answer the question "{self.description}". Do not invoke any tools if you already have answer in the context.\n\n'
                + f"<context>{previous_results}</context>"
            )
            self._response = prompt.invoke(api)
            self.results = self._response["raw_content"]
            self.evaluated = True

    def __str__(self):
        """
        Node(name=..., description=...)
          |-Node(name=..., description=...)
          |-Node(name=..., description=...)
        """
        return f"Node(name={self.name}, children={[x.name for x in self.children]})"


@llm_tool
def population_of_country(country_name: str, year: int) -> int:
    """
    Returns the population of a country in the specified year
    """
    if country_name.lower() == "india":
        return "4 billion"
    else:
        return "2 billion"


@llm_tool
def noop(*args, **kwargs) -> None:
    """
    Does nothing.
    This is typically used at the root of the DAG if no computation is required there.
    """
    pass


def reasoning(question: str) -> str:
    """
    Provides an answer to the question. The answer is something an AI assistant would provide
    """
    response = api.invoke(question, tokens=1024)
    return response["raw_content"]


def convert_json_to_dag(node_list):
    dag = {}
    for js_node in node_list:
        dag[js_node["name"]] = Node(
            js_node["name"], js_node["description"], children=[]
        )
    for js_node in node_list:
        node = dag[js_node["name"]]
        node.children = [dag[x] for x in js_node.get("children", [])]
        for child in node.children:
            if node not in child.previous:
                child.previous.append(node)

    return dag["root"]


prompt = ToolPrompt(
    "Which country is more populated in the year 2022? is it India or China?",
    system_prompt_template=f"""
    In this environment you have access to a set of tools. Output a reasoning DAG (Directed Acyclic Graph) model
    that would help in answering the user request. Your output should only contain the <dag> xml. 
    here's an example dag. The user's question is in the root nodes description. Each node name is unique.
    The tools provided for this example are 'no-operation', 'multiply' and 'sum'. The users question is:
    "Calculate the sum of 23 and 10. Calculate the sum of 2 and 1. Multiply both the results"

    <dag>
    <node>
    <name>root</name>
    <description>No operation</description>
    <children>
      sum1,sum2
    </children>
    <previous>None</previous>
    </node>
    <node>
    <name>sum1</name>
    <description>Calculate the sum of 23 and 10</description>
    <children>
      multiply
    </children>
    <previous>root</previous>
    </node>
    <node>
    <name>sum2</name>
    <description>Calculate the sum of 2 and 1</description>
    <children>
      multiply
    </children>
    <previous>root</previous>
    </node>
    <node>
    <name>multiply1</name>
    <description>Multiply the results</description>
    </node>
    <previous>sum1,sum2</previous>
    </dag>



    <tools>
    {"\n".join([x['description'] for x in LLMFNS])}
    </tools>

    Assistant:
    <dag>
    """,
)
resp = prompt.invoke(api)
pr(resp["parsed_objects"])
if "dag" in resp["parsed_objects"]:
    root = convert_json_to_dag(resp["parsed_objects"]["dag"])
# print(resp["raw_content"])

current = [root]
while current:
    next_depth = []
    for node in current:
        print(node)
        node.evaluate()
        # if node.name in ["compare", "compare_populations", "compare_pop"]:
        #     pr(node._response)
        if node.evaluated:
            print(f"  Results: {node.results}")
        else:
            print("  unable to evaluate")
        for child in node.children:
            if child not in next_depth:
                next_depth.append(child)
    current = next_depth
