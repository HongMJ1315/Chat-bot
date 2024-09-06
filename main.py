import discord
from discord.ext import commands
import chinese_converter
from langchain_community.llms import Ollama
import asyncio
import io
import time
import subprocess
import numpy as np
import pyaudio
from config import *
import concurrent.futures
import speech_recognition as sr

from TTS.TTService import TTService


llm = Ollama(base_url=f"http://{LLM_HOST}:{LLM_PORT}", model="qwen2:7b", temperature=0.7, keep_alive="20m")

intents = discord.Intents.default()
intents.message_content = True  # 啟用 message content intent
intents.guilds = True  # 必須啟用 guild intents 以獲取伺服器的事件

autoreply_channel = {}

bot = commands.Bot(command_prefix="!", intents=intents)



# audio_queue = asyncio.Queue()  # 音頻播放隊列
tts_service = None
is_playing = {}  # 使用字典來管理每個伺服器的播放狀態
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)  # 新增線程池
audio_queues = {}  # 使用字典來管理每個伺服器的音頻播放隊列
recognizer = sr.Recognizer()
audio_tasks = {}
listener_tasks = {}

def model_init():
    global tts_service
    config_combo = ("models/paimon6k.json", "models/paimon6k_390k.pth")

    cfg, model = config_combo
    tts_service = TTService(cfg, model, 'test', 1)

async def audio_player(ctx):
    guild_id = ctx.guild.id
    while True:
        if ctx.voice_client is None:
            await asyncio.sleep(1)
            continue

        if not is_playing[guild_id] and not audio_queues[guild_id].empty():
            is_playing[guild_id] = True
            audio_data, sampling_rate = await audio_queues[guild_id].get()

            process = subprocess.Popen(
                ['ffmpeg', '-f', 's16le', '-ar', str(sampling_rate), '-ac', '1', '-i', 'pipe:0', '-f', 'opus', 'pipe:1'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )

            stdout, _ = process.communicate(input=audio_data)
            audio_stream = io.BytesIO(stdout)
            audio_source = discord.FFmpegPCMAudio(audio_stream, pipe=True)

            def after_playing(error):
                global is_playing
                if error:
                    print(f"Error playing audio: {error}")
                is_playing[guild_id] = False
                audio_queues[guild_id].task_done()

            await asyncio.sleep(0.1)  # 缓冲以确保平滑播放
            ctx.voice_client.play(audio_source, after=after_playing)

            while ctx.voice_client.is_playing():
                await asyncio.sleep(0.1)

        await asyncio.sleep(0.1)
            
def generate_audio_stream(speak_content: str):
    global tts_service
    audio = tts_service.read(speak_content)
    audio = (audio * np.iinfo(np.int16).max).astype(np.int16)
    return audio.tobytes(), tts_service.hps.data.sampling_rate


async def add_to_queue(ctx, text):
    guild_id = ctx.guild.id

    if guild_id not in audio_queues:
        audio_queues[guild_id] = asyncio.Queue()

    if guild_id not in is_playing:
        is_playing[guild_id] = False

    async with asyncio.Lock():
        audio_data, sampling_rate = await asyncio.get_event_loop().run_in_executor(
            executor, generate_audio_stream, text
        )

        await audio_queues[guild_id].put((audio_data, sampling_rate))

    if not is_playing[guild_id]:
        bot.loop.create_task(audio_player(ctx))

        
async def get_llm_response(prompt, timeout=120):
    loop = asyncio.get_event_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(executor, llm.invoke, prompt),
            timeout=timeout
        )
        return chinese_converter.to_traditional(response)
    except asyncio.TimeoutError:
        return "抱歉，模型回應時間過長。請稍後再試。"
    
async def listen_and_speak(ctx, voice_client):
    recognizer.energy_threshold = 4000  # 手動調整靈敏度（越高越不敏感）

    # 自動調整靈敏度 (建議在安靜環境中使用一次)
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    while True:
        with sr.Microphone() as source:
            print("請說話...")
            try:
                loop = asyncio.get_event_loop()

                # 將同步的 listen 函數放入執行緒池中
                audio = await loop.run_in_executor(None, recognizer.listen, source, 10)  # 設定超時與語音限制
                # audio = recognizer.listen(source, timeout=10)  # 等待最多10秒來檢測語音開始
                print("已經捕捉到語音輸入，處理中...")

                # 嘗試使用Google Web Speech API進行語音轉文字
                try:
                    # 使用執行緒池來非同步執行阻塞的 Google 語音識別
                    text = await loop.run_in_executor(None, recognizer.recognize_google, audio, None, 'zh-TW')
                    print(f"你說了: {text}")

                    # 使用 LLM 生成回覆
                    prompt = LLM_PROMPT + LLM_REPLY_PROMPT + text
                    response = await get_llm_response(prompt)
                    response = chinese_converter.to_traditional(response)
                    print(f"回應: {response}")

                    # 播放 LLM 回覆的 TTS 音頻
                    await add_to_queue(ctx, response)
                    
                except sr.UnknownValueError:
                    print("抱歉，我無法理解您說的話。")
                except sr.RequestError as e:
                    print(f"無法連接到Google Web Speech API; {e}")

            except sr.WaitTimeoutError:
                print("沒有檢測到語音輸入。")

        await asyncio.sleep(1)  # 添加短暫的休眠以避免占用過多資源


# 機器人加入伺服器時觸發事件
@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        autoreply_channel[channel.id] = False
    print(f'Added all text channels from guild: {guild.name} to autoreply_channel with default value False.')

# 如果收到!enable指令，將當前頻道設為自動回復啟用狀態
@bot.command()
async def enable(ctx):
    autoreply_channel[ctx.channel.id] = True
    print(f'自動回復已在此頻道啟用: {ctx.channel.name}')
    await ctx.send(f'自動回復已在此頻道啟用: {ctx.channel.name}')

@bot.command()
async def disable(ctx):
    autoreply_channel[ctx.channel.id] = False
    print(f'自動回復已在此頻道禁用: {ctx.channel.name}')
    await ctx.send(f'自動回復已在此頻道禁用: {ctx.channel.name}')

# 自動回覆消息處理
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if(len(message.content) > 0 and message.content[0] != '!' and autoreply_channel.get(message.channel.id, False)):
        # 獲取最後10則訊息
        history = []
        async for msg in message.channel.history(limit=51):
            history.append(msg)
        history.reverse()
        history = history[:-1]  # 去掉最後一條消息，即當前消息

        conversation = "\n".join([f"{msg.author}: {msg.content}" for msg in history])
        
        # 使用執行緒池運行阻塞操作
        loop = asyncio.get_event_loop()
        prompt = LLM_PROMPT + LLM_LAST_10_MSG + conversation + LLM_REPLY_PROMPT + message.content
        response = await get_llm_response(prompt)

        response = chinese_converter.to_traditional(response)
        # print("message:", LLM_PROMPT + LLM_LAST_10_MSG + conversation + LLM_REPLY_PROMPT + message.content)
        # print("=======")
        # print("response:", response)
        # print("=======")
        # print("message length:", len(response))
        # print()
        # print()
        
        timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        # writ message and response to logs.text
        with open("logs.txt", "a") as f:
            f.write(f"History: \n {conversation}\n Message: \n {message.content}\n")
            f.write(f"Response: \n {response}\n{timestr}\n===========================\n\n")
        

        # 如果消息过长，则分段发送
        if len(response) > 2000:
            for i in range(0, len(response), 2000):
                await message.reply(response[i:i + 2000])
        else:
            await message.reply(response)

    await bot.process_commands(message)  # 確保命令仍能正常運行
    
@bot.command()
async def chat(ctx, *, message: str):
   async with ctx.typing():
        prompt = LLM_PROMPT + LLM_REPLY_PROMPT + message
        response = await get_llm_response(prompt)

        if ctx.voice_client:
            await add_to_queue(ctx, response)

        # print("message:", LLM_PROMPT + LLM_REPLY_PROMPT + message)
        # print("=======")
        # print("response:", response)
        # print("=======")
        # print("message length:", len(response), type(response))
        # print()
        # print()
        
        timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with open("logs.txt", "a") as f:
            f.write(f"Message: \n {message}\n")
            f.write(f"Response: \n {response}\n{timestr}\n===========================\n\n")

        # 若訊息過長，則分段發送
        if len(response) > 2000:
            for i in range(0, len(response), 2000):
                sequence = response[i:i+2000]
                await ctx.reply(sequence)
        else:
            await ctx.reply(response)

@bot.command()
async def listen(ctx, *, message: str):
    if(ctx.author.voice is None):
        await ctx.send("請先加入語音頻道。")
        return
    # 檢查機器人是否已經加入語音頻道 若未加入則提示使用!join指令
    if ctx.voice_client is None:
        await ctx.send("請先加入語音頻道。")
        return
    # 若message為空則提示使用者輸入文字
    if not message:
        await ctx.send("請輸入start/stop")
        return
    guild_id = ctx.guild.id
    if(message == "start"):
        listener_tasks[guild_id] = bot.loop.create_task(listen_and_speak(ctx, ctx.voice_client))  # 將ctx傳入
        await ctx.send("啟動STT")
    elif(message == "stop"):
        listener_tasks[guild_id].cancel()
        del listener_tasks[guild_id]
        await ctx.send("停止STT")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        guild_id = ctx.guild.id
        audio_tasks[guild_id] = bot.loop.create_task(audio_player(ctx))

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.guild.voice_client.disconnect()
        guild_id = ctx.guild.id
        if guild_id in is_playing:
            is_playing[guild_id] = False
        if(guild_id in audio_tasks):
            audio_tasks[guild_id].cancel()
            del audio_tasks[guild_id]

@bot.command()
async def tts(ctx, *, message: str):
    if ctx.voice_client:
        print('================ctx==================')
        print(ctx)
        print('=====================================')

        await add_to_queue(ctx, message)
    else:
        await ctx.send("請先加入語音頻道")


# 機器人啟動事件
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

def start_bot(token):
    model_init()
    bot.run(token)

# 啟動機器人
start_bot(TOKEN)
