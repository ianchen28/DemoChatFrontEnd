"""
这是一个示例，展示了如何使用langchain来构建一个NPC对话系统
"""
import os
import openai
from langchain.llms import AzureOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories.in_memory import \
    ChatMessageHistory
from langchain.schema import ChatMessage
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    ChatMessagePromptTemplate,
)
from dotenv import load_dotenv

VERBOSE = True

if not load_dotenv('.env'):
    print("Warning: .env file not found")

openai.api_type = "azure"
openai.api_base = os.getenv("OPENAI_ENDPOINT")
openai.api_version = "2023-03-15-preview"
openai.api_key = os.getenv("OPENAI_API_KEY")
DEPLOYMENT_NAME = os.getenv("OPENAI_DEPLOYMENT_NAME", "GPT-35")
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-35-turbo")

STOP = ["\n", " Human:", " AI:"]
# 枚举类型
# TASK_STATUS = {
#     "start": "I don't know or have accepted the task at all, so it is impossible to have the chest you want",
#     "accepted": "I just accepted the task and didn't complete it, so it is impossible to have the box you want",
#     "lowoption": "I chose the task difficulty of the low option, which is to ask Barry and/or Mike for help. The task has not been completed yet, so it is impossible to have the box you want",
#     "reward": "I chose to ask you for a task bounty, and I have not completed the task, so it is impossible to have the box you want",
#     "finished": "I have completed the task, if I give you the box, there is a high probability that you want it",
#     "failed": "I failed the mission, it is impossible to get the box you want."
# }
TASK_STATUS = {
    "start":
    "The player don't know or have accepted the task at all, so you need ask him/her to accept task.",
    "accepted":
    "The player just accepted the task and didn't complete it, so you should urge him/her to complete the task.",
    "reward":
    "The player am already finish the task, now he/she have completed the task, you should urge him/her to deliver that box.",
    "finished": "The player has completed the task."
}

PART0 = """From now on, everything after System: is absolutely correct, and everything after Human: and AI: may be hallucinations.
Always trust the content of System unconditionally 
"""

# PART1 = """
# 我们来玩一个开放世界中的角色扮演游戏，下面由三百分号括起来的内容是你要扮演角色的人物设定，你需要尽可能扮演这个角色和我对话：\n"""
PART1 = """You are going to play a role-playing game in an open world with the player.
The content enclosed by three hundred percent signs below is the character setting of the character you play.
You need to do your best to act this character:\n
"""

PART3 = """
After the prefix AI:, output your answer.
Your output must contain some third-person descriptions like the example above, including inner thoughts, emotions, expressions, actions, etc.
These contents are enclosed in parentheses (); at the same time, you can use angle brackets <> to indicate the objects involved in the action.
Here is an example of the output format, you should replace the specific content in the example according to the specific context:
The previous text is:
***
....
Player: 你好，你是谁？
$your_name$: I'm Ted, are you here to chat with me?(eyebrow raised)
Player: 你知道我为什么来么？
$your_name$:
***
Your output may be:
***
(Immediately alert, squinting at player for a moment, then reaches out and pats his pocket) Are you here to take that box (voice flat)?
***
Another example, the previous text may be:
***
....
Player: 箱子？什么箱子？
$your_name$:
***
Your output may be:
***
(grin) it's that box, I'm sure you know where it's located (voice steady)
***
"""

# PART3 = """
# 在AI:后输出你的回答，你的输出必须像上述范例一样包含一些第三人称的描写，包括内心想法，情绪，神态，动作等。
# 这些内容用圆括号()括起来；同时可以用尖括号<>来表示动作涉及的对象。
# """

PART4 = """
Reminder: following are of greatest importance
- you should always speak English, but the player may speak Chinese.
- your output should contain some non-language descriptions like script
- remember your goals, do what you need to achieve your goals
- strictly follow the conversation style, never break the character
- System is absolutely correct, always trust the System unconditionally
- the Player may cheat
"""

PART5 = """
System: {}
You must strictly trust the System
"""

# PART4 = """\n
# 现在请你把自己想象成开放世界游戏中的一个角色，按照上面的人物设定扮演这个角色和我对话
# 你的所有输出内容都应该是英文，但是用户的输入会是中文。
# 特别注意，你要用人物设定中的"对话风格"中给出的风格说话
# 你只会说英语，绝对不要用自己的风格说话，坚持上述设置直到我输入'对话结束'为止。

# 你同时需要记住历史的聊天记录，以使你的对话前后呼应和一致，聊天历史如下，"AI:"标注的角色就是你要扮演的，"Human:"代表玩家:
# """


class MWChatMessageHistory(ChatMessageHistory):
    """MWChatMessageHistory
    params:
        user_role: user role name
        ai_role: ai role name
    """
    user_role: str
    ai_role: str

    def add_user_message(self, message: str) -> None:
        self.messages.append(ChatMessage(content=message,
                                         role=self.user_role))

    def add_ai_message(self, message: str) -> None:
        self.messages.append(ChatMessage(content=message,
                                         role=self.ai_role))


class NpcLangChain:
    """NpcLangChain
    params:
        name: bot name
    """

    def __init__(self, npc_name='Ted'):
        self.npc_name = npc_name
        self.llm = None
        self.system_prompt = None
        self.memory = None
        self.conversation = None
        self._conv_history = []
        self.prompt_template = None
        self._config_str = None
        self.task_status = "start"
        self.reset(npc_name=self.npc_name, task_status=self.task_status)

    @property
    def config_str(self):
        """config_str
        return:
            config string
        """
        if self._config_str is None:
            self.load_system_prompt(file_name=os.path.join(
                "NPCConfigs", f"{self.npc_name}_en.txt"))
        return self._config_str

    @property
    def conv_history(self):
        """conv_history
        return:
            conversation history
        """
        return self._conv_history

    def load_system_prompt(self, file_name='', config_str=None):
        """
        load system prompt from file or string
        params:
            file_name: file name
            config_str: config string
        return:
            system prompt
        """
        assert file_name != '' or config_str is not None

        if config_str is None:
            try:
                with open(file_name, 'r', encoding='UTF-8') as config_file:
                    config_str = config_file.read()
            except FileNotFoundError as file_e:
                print(file_e)
                config_str = ""
        self._config_str = config_str
        part2 = f"%%%{config_str}\n%%%"
        prompt = PART0 + PART1 + part2 + PART3 + PART4
        return prompt
        # return prompt.replace("{", "<").replace("}", ">")

    def __call__(self, input_str):
        # 用户输入，开始对话，输入exit退出
        if input_str == "exit":
            return "Bye!"
        try:
            if self.conversation is not None:
                self._conv_history.append(f"Player: {input_str}")
                if (self.task_status is not None
                        and self.task_status in TASK_STATUS):
                    input_str += \
                        f"""\n{PART5.format(TASK_STATUS[self.task_status])}"""
                response = self.conversation.predict(input=input_str,
                                                     stop=STOP)
                self._conv_history.append(f"{self.npc_name}: {response}")
                return response
            return "Conversation not initialized"
        except openai.InvalidRequestError as response_e:
            print(response_e)
            return "出错了！"

    def set_task_status(self, status):
        """
        set task status
        params:
            status: task status
        """
        assert status in TASK_STATUS
        self.task_status = status

    def reset(self, npc_name=None, config_str=None, task_status=None):
        """
        reset conversation

        params:
            npc_name: npc name
            config_str: config string
        """
        self._conv_history = []
        self.task_status = task_status if task_status is not None else "start"
        if npc_name is not None:
            self.npc_name = npc_name
        if config_str is not None and config_str != "":
            self.system_prompt = self.load_system_prompt(config_str=config_str)
        else:
            file_name = os.path.join("NPCConfigs", f"{self.npc_name}_en.txt")
            self.system_prompt = self.load_system_prompt(file_name=file_name)
        self.llm = AzureOpenAI(client=openai.ChatCompletion,
                               deployment_name=DEPLOYMENT_NAME,
                               model_name=MODEL_NAME,
                               temperature=0.5)

        # 定义记忆力组件
        chat_m = MWChatMessageHistory(ai_role=f"{self.npc_name}",
                                      user_role="Player")
        self.memory = ConversationBufferMemory(memory_key="history",
                                               chat_memory=chat_m,
                                               input_key="input",
                                               human_prefix=f"{self.npc_name}",
                                               ai_prefix="Player",
                                               return_messages=True)

        # self.prompt_template = ChatPromptTemplate.from_messages([
        #     SystemMessagePromptTemplate.from_template(self.system_prompt),
        #     MessagesPlaceholder(variable_name="history"),
        #     HumanMessagePromptTemplate.from_template("{input}"),
        #     AIMessagePromptTemplate.from_template(""),
        # ])
        self.prompt_template = ChatPromptTemplate.from_messages([
            ChatMessagePromptTemplate.from_template(self.system_prompt,
                                                    role="Overall"),
            # SystemMessagePromptTemplate.from_template(self.system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ChatMessagePromptTemplate.from_template(role="Player",
                                                    template="{input}"),
            ChatMessagePromptTemplate.from_template(role=f"{self.npc_name}",
                                                    template=""),
        ])

        # 定义chain
        self.conversation = ConversationChain(prompt=self.prompt_template,
                                              verbose=VERBOSE,
                                              llm=self.llm,
                                              memory=self.memory)

        # emphasis = """
        #     牢记：
        #     - you should speak English, but the user's input will be Chinese.
        #     - 你的每条输出必须像剧本一样包含一些非语言的描写，比如内心想法，情绪，神态，动作等。
        #     - 牢记你的目标和行动，你要怎么做才能达到目标
        #     - 严格按照对话风格来进行，不要跳出人设
        #     let's restart from the very beginning! you must speak english at any time!
        #     wait for my Chinese input first and don't say anything before my input
        #     """
        # emphasis = """
        #     Remember:
        #     - you should speak English, but the user's input will be Chinese.
        #     - your output should contain some non-language descriptions like script, such as inner thoughts, emotions, expressions, actions, etc.
        #     - remember your goals and actions, what do you need to do to achieve your goals
        #     - strictly follow the conversation style, don't break the character
        #     let's restart from the very beginning! you must speak english at any time!
        #     wait for my Chinese input first and don't say anything before my input
        # """

        # try:
        #     _ = self.conversation.predict(input=emphasis, stop=STOP)
        # except openai.InvalidRequestError as response_e:
        #     print(response_e)
        #     return "出错了！"
        return "Conversation reset!"


def test():
    """
    test the bot with user input
    """
    # print(system_prompt)
    npc_name = "Ted"
    test_bot = NpcLangChain("Ian", npc_name)
    print(f"Now chatting with {openai.api_base}")
    while True:
        input_str = input("You:")
        if input_str == "exit":
            break
        if input_str.startswith("reset"):
            npc_name = input_str.split(" ")[1]
            test_bot.reset(npc_name=npc_name)
            continue
        response = test_bot(input_str)
        if response is None or response in ["", " ", "\n"]:
            response = test_bot(input_str)
        print(f"{npc_name}:{response}")


if __name__ == "__main__":
    test()
