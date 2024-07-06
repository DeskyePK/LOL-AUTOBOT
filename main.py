import time
import requests
import urllib3
from lcu_driver import Connector
import webbrowser
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tb 
import os
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

connector = Connector()
global am_i_assigned, am_i_picking, am_i_banning, ban_number, phase, picks, bans, in_game, bot_active
am_i_assigned = False
am_i_banning = False
am_i_picking = False
in_game = False
phase = ''
picks = ["", "", "", ""]
bans = ["", "", "", ""]
pick_number = 0
ban_number = 0
bot_active = False

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
       
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def center_window(root, width=320, height=500):
  
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    

    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    

    root.geometry(f'{width}x{height}+{x}+{y}')

@connector.ready
async def connect(connection):
    global summoner_id, champions_map
    temp_champions_map = {}
    summoner = await connection.request('get', '/lol-summoner/v1/current-summoner')
    summoner_to_json = await summoner.json()
    summoner_id = summoner_to_json['summonerId']
    champion_list = await connection.request('get', f'/lol-champions/v1/inventories/{summoner_id}/champions-minimal')

    champion_list_to_json = await champion_list.json()
    for i in range(len(champion_list_to_json)):
        temp_champions_map.update({champion_list_to_json[i]['name']: champion_list_to_json[i]['id']})
    champions_map = temp_champions_map

@connector.ws.register('/lol-matchmaking/v1/ready-check', event_types=('UPDATE',))
async def ready_check_changed(connection, event):
    if event.data['state'] == 'InProgress' and event.data['playerResponse'] == 'None':
        await connection.request('post', '/lol-matchmaking/v1/ready-check/accept', data={})

@connector.ws.register('/lol-champ-select/v1/session', event_types=('CREATE', 'UPDATE',))
async def champ_select_changed(connection, event):
    global am_i_assigned, pick_number, ban_number, am_i_banning, am_i_picking, phase, bans, picks, have_i_prepicked, in_game, action_id
    if not bot_active:
        return
    
    have_i_prepicked = False
    lobby_phase = event.data['timer']['phase']

    local_player_cell_id = event.data['localPlayerCellId']
    for teammate in event.data['myTeam']:
        if teammate['cellId'] == local_player_cell_id:
            assigned_position = teammate['assignedPosition']
            am_i_assigned = True

    for action in event.data['actions']:
        for actionArr in action:
            if actionArr['actorCellId'] == local_player_cell_id and actionArr['isInProgress'] == True:
                phase = actionArr['type']
                action_id = actionArr['id']
                if phase == 'ban':
                    am_i_banning = actionArr['isInProgress']
                if phase == 'pick':
                    am_i_picking = actionArr['isInProgress']

    if phase == 'ban' and lobby_phase == 'BAN_PICK' and am_i_banning:
        while am_i_banning:
            try:
                await connection.request('patch', '/lol-champ-select/v1/session/actions/%d' % action_id,
                                         data={"championId": champions_map[bans[ban_number]], "completed": True})
                ban_number += 1
                am_i_banning = False
            except (Exception,):
                ban_number += 1
                if ban_number >= len(bans):
                    ban_number = 0
    if phase == 'pick' and lobby_phase == 'BAN_PICK' and am_i_picking:
        while am_i_picking:
            try:
                await connection.request('patch', '/lol-champ-select/v1/session/actions/%d' % action_id,
                                         data={"championId": champions_map[picks[pick_number]], "completed": True})
                pick_number += 1
                am_i_picking = False
            except (Exception,):
                pick_number += 1
                if pick_number >= len(picks):
                    pick_number = 0
    if lobby_phase == 'PLANNING' and not have_i_prepicked:
        try:
            await connection.request('patch', '/lol-champ-select/v1/session/actions/%d' % action_id,
                                     data={"championId": champions_map['Teemo'], "completed": False})
            have_i_prepicked = True
        except (Exception,):
            print(Exception)
    if lobby_phase == 'FINALIZATION':
        while not in_game:
            try:
                request_game_data = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', verify=False)
                game_data = request_game_data.json()['gameData']['gameTime']
                if game_data > 0 and not in_game:
                    print("Game found!")
                time.sleep(2)
            except (Exception,):
                print('Esperando Inicio de Partida...')
                time.sleep(2)
    pick_number = 0
    ban_number = 0

@connector.ws.register('/lol-gameflow/v1/gameflow-phase', event_types=('UPDATE',))
async def gameflow_phase_changed(connection, event):
    global in_game
    if event.data == 'EndOfGame':
        in_game = False
        print('Jogo Terminado. Esperando Proxima Partida ...')
        time.sleep(5)

@connector.close
async def disconnect(_):
    print('O cliente foi fechado !')
    await connector.stop()

def toggle_bot():
    global bot_active
    bot_active = not bot_active
    if bot_active:
        start_button.config(text="PARAR BOT", style="Stop.TButton")
    else:
        start_button.config(text="INICIAR BOT", style="Start.TButton")
    threading.Thread(target=connector.start if bot_active else connector.stop, daemon=True).start()

def save_picks():
    global picks
    picks[0] = pick1_entry.get()
    picks[1] = pick2_entry.get()
    picks[2] = pick3_entry.get()
    picks[3] = pick4_entry.get()
    messagebox.showinfo("Info", "Picks salvos com sucesso!")

def save_bans():
    global bans
    bans[0] = ban1_entry.get()
    bans[1] = ban2_entry.get()
    bans[2] = ban3_entry.get()
    bans[3] = ban4_entry.get()
    messagebox.showinfo("Info", "Bans salvos com sucesso!")

def show_picks_tab():
    tab_control.select(tab_picks)

def show_bans_tab():
    tab_control.select(tab_bans)

def open_github(event):
    webbrowser.open_new("https://github.com/DeskyePK/LOL-AUTOBOT")

root = tb.Window(themename="solar")
root.title("LOL AUTO BOT - DESKYE")
center_window(root, 320, 500)  # Centraliza a janela
root.resizable(False, False) 

style = ttk.Style()
style.configure("TNotebook", background="white")
style.configure("TFrame", background="white")
style.configure("TButton", background="white")
style.configure("TLabel", background="white", foreground="black")

# Estilos personalizados para os botões
style.configure("Stop.TButton", background="red", foreground="white")

tab_control = ttk.Notebook(root)
tab_start = ttk.Frame(tab_control)
tab_picks = ttk.Frame(tab_control)
tab_bans = ttk.Frame(tab_control)

tab_control.add(tab_start, text="INICIO")
tab_control.add(tab_picks, text="PICKS")
tab_control.add(tab_bans, text="BANS")
tab_control.pack(expand=1, fill="both")

# Ocultar as abas
tab_control.hide(tab_picks)
tab_control.hide(tab_bans)

# Adicionando a logo
logo_path = resource_path("LOGO.png")
logo = tk.PhotoImage(file=logo_path)
logo_label = ttk.Label(tab_start, image=logo)
logo_label.pack(pady=20)

icon_path = resource_path("icone.ico")
root.iconbitmap(icon_path)

# Botões Pickar e Banir
button_frame = ttk.Frame(tab_start)
button_frame.pack(pady=10)

pickar_button = ttk.Button(button_frame, text="PICKAR", command=show_picks_tab, takefocus=False)
pickar_button.pack(side=tk.LEFT, padx=10)

banir_button = ttk.Button(button_frame, text="BANIR", command=show_bans_tab, takefocus=False)
banir_button.pack(side=tk.RIGHT, padx=10)

# Botão Iniciar
start_button = ttk.Button(tab_start, text="INICIAR BOT", command=toggle_bot, style="Start.TButton", takefocus=False)
start_button.pack(fill=tk.X, pady=10)


for tab in [tab_picks, tab_bans]:
    tab.grid_columnconfigure(0, weight=1)
    tab.grid_columnconfigure(1, weight=1)

# Picks
ttk.Label(tab_picks, text="Pick 1:").grid(column=0, row=0, padx=10, pady=10, sticky="e")
pick1_entry = ttk.Entry(tab_picks)
pick1_entry.grid(column=1, row=0, padx=10, pady=10, sticky="w")

ttk.Label(tab_picks, text="Pick 2:").grid(column=0, row=1, padx=10, pady=10, sticky="e")
pick2_entry = ttk.Entry(tab_picks)
pick2_entry.grid(column=1, row=1, padx=10, pady=10, sticky="w")

ttk.Label(tab_picks, text="Pick 3:").grid(column=0, row=2, padx=10, pady=10, sticky="e")
pick3_entry = ttk.Entry(tab_picks)
pick3_entry.grid(column=1, row=2, padx=10, pady=10, sticky="w")

ttk.Label(tab_picks, text="Pick 4:").grid(column=0, row=3, padx=10, pady=10, sticky="e")
pick4_entry = ttk.Entry(tab_picks)
pick4_entry.grid(column=1, row=3, padx=10, pady=10, sticky="w")

picks_button = ttk.Button(tab_picks, text="SALVAR PICKS", command=save_picks, takefocus=False)
picks_button.grid(column=0, row=4, columnspan=2, pady=20)

# Bans
ttk.Label(tab_bans, text="Ban 1:").grid(column=0, row=0, padx=10, pady=10, sticky="e")
ban1_entry = ttk.Entry(tab_bans)
ban1_entry.grid(column=1, row=0, padx=10, pady=10, sticky="w")

ttk.Label(tab_bans, text="Ban 2:").grid(column=0, row=1, padx=10, pady=10, sticky="e")
ban2_entry = ttk.Entry(tab_bans)
ban2_entry.grid(column=1, row=1, padx=10, pady=10, sticky="w")

ttk.Label(tab_bans, text="Ban 3:").grid(column=0, row=2, padx=10, pady=10, sticky="e")
ban3_entry = ttk.Entry(tab_bans)
ban3_entry.grid(column=1, row=2, padx=10, pady=10, sticky="w")

ttk.Label(tab_bans, text="Ban 4:").grid(column=0, row=3, padx=10, pady=10, sticky="e")
ban4_entry = ttk.Entry(tab_bans)
ban4_entry.grid(column=1, row=3, padx=10, pady=10, sticky="w")

bans_button = ttk.Button(tab_bans, text="SALVAR BANS", command=save_bans, takefocus=False)
bans_button.grid(column=0, row=4, columnspan=2, pady=20)

footer_frame = ttk.Frame(root)
footer_frame.pack(side=tk.BOTTOM, pady=10)

footer_label = ttk.Label(footer_frame, text="Acompanhe no meu ")
footer_label.pack(side=tk.LEFT)

github_link = ttk.Label(footer_frame, text="GitHub!", foreground="lightblue", cursor="hand2")
github_link.pack(side=tk.LEFT)
github_link.bind("<Button-1>", open_github)

root.mainloop()