import re,os
from kivy.lang import Builder
import numpy as np
import torch
import torch.nn as nn
import pybullet as p
from panda3d_kivy.mdapp import MDApp

from direct.gui.DirectGui import *
from panda3d.core import AmbientLight, DirectionalLight, Spotlight, PerspectiveLens

import math
import imageio
import time

from surrol.gui.scene import Scene, GymEnvScene
from surrol.gui.application import Application, ApplicationConfig
from surrol.tasks.ecm_misorient import MisOrient
from surrol.tasks.ecm_reach import ECMReach
from surrol.tasks.ecm_active_track import ActiveTrack
from surrol.tasks.ecm_static_track import StaticTrack
from surrol.tasks.gauze_retrieve import GauzeRetrieve
from surrol.tasks.needle_reach import NeedleReach
from surrol.tasks.needle_pick import NeedlePick
from surrol.tasks.peg_board import PegBoard
from surrol.tasks.peg_board_bimanual import BiPegBoard
from surrol.tasks.peg_transfer import PegTransfer 
from surrol.tasks.peg_transfer_RL import PegTransferRL
from surrol.tasks.needle_regrasp_bimanual import NeedleRegrasp
from surrol.tasks.peg_transfer_bimanual import BiPegTransfer
from surrol.tasks.pick_and_place import PickAndPlace
from surrol.tasks.match_board import MatchBoard
from surrol.tasks.match_board_ii import MatchBoardII 
from surrol.utils.pybullet_utils import get_link_pose
from surrol.tasks.needle_the_rings import NeedleRings
# from surrol.tasks.match_board_ii import BiMatchBoard
from surrol.tasks.ecm_env import EcmEnv, goal_distance,reset_camera
from surrol.robots.ecm import RENDER_HEIGHT, RENDER_WIDTH, FoV
from surrol.robots.ecm import Ecm

from haptic_src.touch_haptic import initTouch_right, closeTouch_right, getDeviceAction_right, startScheduler, stopScheduler
from haptic_src.touch_haptic import initTouch_left, closeTouch_left, getDeviceAction_left
from direct.task import Task
from surrol.utils.pybullet_utils import step

from dVTrainer import Net, Console
from dVTrainer.data_collector import DataLogger
from dVTrainer.random_experiment_new import user_num
from dVTrainer.obs_controller import OBSController
from scipy.spatial.transform import Rotation as R

app = None
hint_printed = False
resetFlag = False
def open_scene(id):
    global app, hint_printed,resetFlag

    scene = None
    menu_dict = {0:StartPage(),1:ECMPage(),2:NeedlePage(),3:PegPage(),4:PickPlacePage()}
    task_list =[NeedlePick,PegTransfer,NeedleRegrasp,BiPegTransfer,PickAndPlace,BiPegBoard,NeedleRings,MatchBoard,ECMReach,MisOrient,StaticTrack,ActiveTrack,NeedleReach,GauzeRetrieve]
    bimanual_list=[9,10,11,12,16,17,18]
    if id < 5:
        scene = menu_dict[id]
    elif id in bimanual_list:
        
        jaws=[1.0, 1.0] if id==9 or id==10 else [1.0,1.0]
        scene = SurgicalSimulatorBimanual(task_list[(id-5)//2], {'render_mode': 'human'}, jaw_states=jaws,id=id) if id %2==1 and id!=9 else \
        SurgicalSimulatorBimanual(task_list[(id-5)//2], {'render_mode': 'human'}, jaw_states=jaws,id=id,demo=1)
    else:
        if id ==15:
            scene = SurgicalSimulator(PegBoard,{'render_mode': 'human'},id)
        elif id ==8:
            scene = SurgicalSimulator(PegTransferRL,{'render_mode': 'human'},id,demo=1)
        elif id ==6:
            scene = SurgicalSimulator(NeedlePick,{'render_mode': 'human'},id,demo=1)
        else:
            scene = SurgicalSimulator(task_list[(id-5)//2],{'render_mode': 'human'},id) if id%2==1 else\
            SurgicalSimulator(task_list[(id-5)//2],{'render_mode': 'human'},id,demo=1)
    # if id == 0:
    #     scene = StartPage()
    # elif id == 1:
    #     scene = ECMPage()    
    # elif id == 2:
    #     scene = NeedlePage()
    # elif id == 3:
    #     scene = PegPage()
    # elif id == 4:
    #     scene = PickPlacePage()
    # elif id == 5:
    #     scene = SurgicalSimulator(NeedlePick, {'render_mode': 'human'},id)
    # elif id == 6:
    #     scene = SurgicalSimulator(NeedlePick, {'render_mode': 'human'},id,demo=1)
    # elif id == 7:
    #     scene = SurgicalSimulator(PegTransfer, {'render_mode': 'human'},id)
    # elif id == 8:
    #     scene = SurgicalSimulator(PegTransfer, {'render_mode': 'human'},id,demo=1)
    # elif id == 9:
    #     scene = SurgicalSimulatorBimanual(NeedleRegrasp, {'render_mode': 'human'}, jaw_states=[1.0, -0.5],id=id)
    # elif id == 10:
    #     scene = SurgicalSimulatorBimanual(NeedleRegrasp, {'render_mode': 'human'}, jaw_states=[1.0, -0.5],id=id,demo=1)
    # elif id == 11:
    #     scene = SurgicalSimulatorBimanual(BiPegTransfer, {'render_mode': 'human'}, jaw_states=[1.0, 1.0],id=id)
    # elif id == 12:
    #     scene = SurgicalSimulatorBimanual(BiPegTransfer, {'render_mode': 'human'}, jaw_states=[1.0, 1.0],id=id,demo=1)
    # elif id == 13:
    #     scene = SurgicalSimulator(PickAndPlace, {'render_mode': 'human'},id)
    # elif id == 14:
    #     scene = SurgicalSimulator(PickAndPlace, {'render_mode': 'human'},id,demo=1)
    # elif id == 15:
    #     scene = SurgicalSimulator(PegBoard, {'render_mode': 'human'},id)
    # elif id == 16:
    #     scene = SurgicalSimulator(PegBoard, {'render_mode': 'human'},id)
    # elif id == 17:
    #     scene = SurgicalSimulatorBimanual(NeedleRings, {'render_mode': 'human'}, jaw_states=[1.0, 1.0],id=id)
    # elif id == 18:
    #     scene = SurgicalSimulatorBimanual(NeedleRings, {'render_mode': 'human'}, jaw_states=[1.0, 1.0],id=id,demo=1)
    # elif id == 19:
    #     scene = SurgicalSimulator(MatchBoard, {'render_mode': 'human'},id)
    # elif id == 20:
    #     scene = SurgicalSimulator(MatchBoard, {'render_mode': 'human'},id,demo=1)
    # elif id == 21:
    #     scene = SurgicalSimulator(ECMReach, {'render_mode': 'human'},id)
    # elif id == 22:
    #     scene = SurgicalSimulator(ECMReach, {'render_mode': 'human'},id,demo=1)
    # elif id == 23:
    #     scene = SurgicalSimulator(MisOrient, {'render_mode': 'human'},id)
    # elif id == 24:
    #     scene = SurgicalSimulator(MisOrient, {'render_mode': 'human'},id,demo=1)
    # elif id == 25:
    #     scene = SurgicalSimulator(StaticTrack, {'render_mode': 'human'},id)
    # elif id == 26:
    #     scene = SurgicalSimulator(StaticTrack, {'render_mode': 'human'},id,demo=1)
    # elif id == 27:
    #     scene = SurgicalSimulator(ActiveTrack, {'render_mode': 'human'},id)
    # elif id == 28:
    #     scene = SurgicalSimulator(ActiveTrack, {'render_mode': 'human'},id,demo=1)
    # elif id == 29:
    #     scene = SurgicalSimulator(NeedleReach, {'render_mode': 'human'},id)
    # elif id == 30:
    #     scene = SurgicalSimulator(NeedleReach, {'render_mode': 'human'},id,demo=1)
    # elif id == 31:
    #     scene = SurgicalSimulator(GauzeRetrieve, {'render_mode': 'human'},id)
    # elif id == 32:
    #     scene = SurgicalSimulator(GauzeRetrieve, {'render_mode': 'human'},id,demo=1)

    # if id in (1, 2) and not hint_printed:
    #     print('Press <W><A><S><D><E><Q><Space> to control the PSM.')
    #     hint_printed = True
    
    if scene:
        app.play(scene)


selection_panel_kv = '''MDBoxLayout:
    orientation: 'vertical'
    spacing: dp(10)
    padding: dp(20)

    MDLabel:
        text: "SurRoL Simulator v2"
        theme_text_color: "Primary"
        font_style: "H6"
        bold: True
        size_hint: 1.0, 0.1

    MDSeparator:

    MDGridLayout:
        cols: 2
        spacing: "30dp"
        padding: "20dp", "10dp", "20dp", "20dp"
        size_hint: 1.0, 0.9
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/ecm_track.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "1. Endoscope Fov Control"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Practise ECM control skills"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn1
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"

        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/needlepick_poster.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "2. Fundamental Actions"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Practise fundamental actions in surgery" 
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn2
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        

        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/pegtransfer_poster.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "3. Basic Robot Skill Training Tasks"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Pratise positioning and orienting objects"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0

                MDRaisedButton:
                    id: btn3
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        

'''      

        # MDCard:
        #     orientation: "vertical"
        #     size_hint: .45, None
        #     height: box_top.height + box_bottom.height

        #     MDBoxLayout:
        #         id: box_top
        #         spacing: "20dp"
        #         adaptive_height: True

        #         FitImage:
        #             source: "images/pick&place.png"
        #             size_hint: 0.5, None
        #             height: text_box.height

        #         MDBoxLayout:
        #             id: text_box
        #             orientation: "vertical"
        #             adaptive_height: True
        #             spacing: "10dp"
        #             padding: 0, "10dp", "10dp", "10dp"

        #             MDLabel:
        #                 text: "4. Pick & Place Tasks"
        #                 theme_text_color: "Primary"
        #                 font_style: "H6"
        #                 bold: True
        #                 adaptive_height: True

        #             MDLabel:
        #                 text: "Practice positioning and orienting objects"
        #                 adaptive_height: True
        #                 theme_text_color: "Primary"

        #     MDSeparator:

        #     MDBoxLayout:
        #         id: box_bottom
        #         adaptive_height: True
        #         padding: "0dp", 0, 0, 0
                
        #         MDRaisedButton:
        #             id: btn4
        #             text: "Play"
        #             size_hint: 0.8, 1.0
        #         MDIconButton:
        #             icon: "application-settings"

Peg_panel_kv = '''MDBoxLayout:
    orientation: 'vertical'


    MDLabel:
        text: "                                             Basic Robot Skill Training Tasks"
        theme_text_color: "Primary"
        font_style: "H4"
        bold: True
        spacing: "10dp"
        size_hint: 1.0, 0.3


    MDSeparator:

    MDGridLayout:
        cols: 2
        spacing: "40dp"
        padding: "20dp", "10dp", "20dp", "20dp"
        size_hint: 1.0, 1.0
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/pegtransfer_poster.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Peg Transfer"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Move the block to the target peg"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn1
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/bipegtransfer_poster.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Bi-Peg Transfer"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Bimanual peg transfer"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn2
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"


        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/pegboard.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Peg Board"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Transfer red ring from peg board to peg on floor"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn3
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/pick&place.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Pick and Place"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Place colored jacks into matching containers"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn4
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/matchboard.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Match Board"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Transfer various objects into matching spaces"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn5
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/needlerings.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Needle the Rings"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Pass a needle through the target ring"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0

                MDRaisedButton:
                    id: btn6
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"



    MDBoxLayout:
        MDRectangleFlatIconButton:
            icon: "exit-to-app"
            id: btn7
            text: "Exit"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1, 0
        MDRectangleFlatIconButton:
            icon: "head-lightbulb-outline"
            id: btn8
            text: "AI Assistant"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1, 0 
        MDRectangleFlatIconButton:
            icon: "chart-histogram"
            id: btn8
            text: "Evaluation"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1,0
        MDRectangleFlatIconButton:
            icon: "help-box"
            id: btn8
            text: "Help"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1,0

'''

PickPlace_panel_kv = '''MDBoxLayout:
    orientation: 'vertical'


    MDLabel:
        text: "                                                              Pick & Place Tasks"
        theme_text_color: "Primary"
        font_style: "H4"
        bold: True
        spacing: "10dp"
        size_hint: 1.0, 0.3


    MDSeparator:

    MDGridLayout:
        cols: 2
        spacing: "40dp"
        padding: "20dp", "10dp", "20dp", "20dp"
        size_hint: 1.0, 1.0
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/gauze_retrieve.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Gauze Retrieve"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: " Pick the gauze and place it at the target position"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn1
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"

        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/pick&place.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Pick and Place"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Place colored jacks into matching colored containers"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn2
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/matchboard.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Match Board"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Pick up various objects and place them into corresponding spaces on the board"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn3
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        


    MDBoxLayout:
        MDRectangleFlatIconButton:
            icon: "exit-to-app"
            id: btn4
            text: "Exit"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1, 0
        MDRectangleFlatIconButton:
            icon: "head-lightbulb-outline"
            id: btn5
            text: "AI Assistant"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1, 0 
        MDRectangleFlatIconButton:
            icon: "chart-histogram"
            id: btn6
            text: "Evaluation"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1,0
        MDRectangleFlatIconButton:
            icon: "help-box"
            id: btn7
            text: "Help"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1,0

'''

needle_panel_kv = '''MDBoxLayout:
    orientation: 'vertical'


    MDLabel:
        text: "                                                        Fundamental Actions"
        theme_text_color: "Primary"
        font_style: "H4"
        bold: True
        spacing: "10dp"
        size_hint: 1.0, 0.3


    MDSeparator:

    MDGridLayout:
        cols: 2
        spacing: "40dp"
        padding: "20dp", "10dp", "20dp", "20dp"
        size_hint: 1.0, 1.0
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/needle_reach.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Needle Reach"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Move the gripper to a randomly sampled position"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn1
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"

        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/gauze_retrieve.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Gauze Retrieve"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Pick the gauze and place it at the target position"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn2
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"

        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/needlepick_poster.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Needle Pick"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Pick up the needle and move to target position"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn3
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"


        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/needleregrasp_poster.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Needle Regrasp"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Bimanual version of needle pick"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn4
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        




    MDBoxLayout:
        MDRectangleFlatIconButton:
            icon: "exit-to-app"
            id: btn5
            text: "Exit"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1, 0
        MDRectangleFlatIconButton:
            icon: "head-lightbulb-outline"
            id: btn6
            text: "AI Assistant"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1, 0 
        MDRectangleFlatIconButton:
            icon: "chart-histogram"
            id: btn6
            text: "Evaluation"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1,0
        MDRectangleFlatIconButton:
            icon: "help-box"
            id: btn6
            text: "Help"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1,0

'''



ECM_panel_kv = '''MDBoxLayout:
    orientation: 'vertical'


    MDLabel:
        text: "                                                     Endoscope Fov Control"
        theme_text_color: "Primary"
        font_style: "H4"
        bold: True
        spacing: "10dp"
        size_hint: 1.0, 0.3


    MDSeparator:

    MDGridLayout:
        cols: 2
        spacing: "40dp"
        padding: "20dp", "10dp", "20dp", "20dp"
        size_hint: 1.0, 1.0
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/ecm_reach.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "ECM Reach"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Move the ECM to a randomly sampled position"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn1
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        
        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/misorient.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "MisOrient"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Adjust ECM to minimize misorientation"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn2
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"


        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/static_track.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Static Track"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Make ECM track a static target cube"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0
                
                MDRaisedButton:
                    id: btn3
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"
        

        MDCard:
            orientation: "vertical"
            size_hint: .45, None
            height: box_top.height + box_bottom.height

            MDBoxLayout:
                id: box_top
                spacing: "20dp"
                adaptive_height: True

                FitImage:
                    source: "images/active_track.png"
                    size_hint: 0.5, None
                    height: text_box.height

                MDBoxLayout:
                    id: text_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: "10dp"
                    padding: 0, "10dp", "10dp", "10dp"

                    MDLabel:
                        text: "Active Track"
                        theme_text_color: "Primary"
                        font_style: "H6"
                        bold: True
                        adaptive_height: True

                    MDLabel:
                        text: "Make ECM track a active target cube"
                        adaptive_height: True
                        theme_text_color: "Primary"

            MDSeparator:

            MDBoxLayout:
                id: box_bottom
                adaptive_height: True
                padding: "0dp", 0, 0, 0

                MDRaisedButton:
                    id: btn4
                    text: "Play"
                    size_hint: 0.8, 1.0
                MDIconButton:
                    icon: "application-settings"




    MDBoxLayout:
        MDRectangleFlatIconButton:
            icon: "exit-to-app"
            id: btn5
            text: "Exit"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1, 0
        MDRectangleFlatIconButton:
            icon: "head-lightbulb-outline"
            id: btn6
            text: "AI Assistant"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1, 0 
        MDRectangleFlatIconButton:
            icon: "chart-histogram"
            id: btn6
            text: "Evaluation"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.primary_color
            size_hint: 0.1,0
        MDRectangleFlatIconButton:
            icon: "help-box"
            id: btn6
            text: "Help"
            text_color: (1, 1, 1, 1)
            icon_color: (1, 1, 1, 1)
            md_bg_color: app.theme_cls.bg_light
            size_hint: 0.1,0


'''
class SelectionUI(MDApp):

    def __init__(self, panda_app, display_region):
        super().__init__(panda_app=panda_app, display_region=display_region)
        self.screen = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.screen = Builder.load_string(selection_panel_kv)
        return self.screen

    def on_start(self):
        self.screen.ids.btn1.bind(on_press = lambda _: open_scene(1))
        self.screen.ids.btn2.bind(on_press = lambda _: open_scene(2))
        self.screen.ids.btn3.bind(on_press = lambda _: open_scene(3))
        # self.screen.ids.btn4.bind(on_press = lambda _: open_scene(4))

        # self.screen.ids.btn11.bind(on_press = lambda _: open_scene(11))

class NeedleUI(MDApp):

    def __init__(self, panda_app, display_region):
        super().__init__(panda_app=panda_app, display_region=display_region)
        self.screen = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.screen = Builder.load_string(needle_panel_kv)
        return self.screen

    def on_start(self):
        self.screen.ids.btn1.bind(on_press = lambda _: open_scene(29))
        self.screen.ids.btn2.bind(on_press = lambda _: open_scene(31))
        self.screen.ids.btn3.bind(on_press = lambda _: open_scene(6))
        self.screen.ids.btn4.bind(on_press = lambda _: open_scene(9))
        self.screen.ids.btn5.bind(on_press = lambda _: open_scene(0))
        self.screen.ids.btn6.bind(on_press = lambda _: open_scene(2))


class PegUI(MDApp):

    def __init__(self, panda_app, display_region):
        super().__init__(panda_app=panda_app, display_region=display_region)
        self.screen = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.screen = Builder.load_string(Peg_panel_kv)
        return self.screen

    def on_start(self):
        self.screen.ids.btn1.bind(on_press = lambda _: open_scene(7))
        self.screen.ids.btn2.bind(on_press = lambda _: open_scene(11))
        self.screen.ids.btn3.bind(on_press = lambda _: open_scene(15))
        self.screen.ids.btn4.bind(on_press = lambda _: open_scene(13))
        self.screen.ids.btn5.bind(on_press = lambda _: open_scene(19))
        self.screen.ids.btn6.bind(on_press = lambda _: open_scene(17))
        self.screen.ids.btn7.bind(on_press = lambda _: open_scene(0))
        self.screen.ids.btn8.bind(on_press = lambda _: open_scene(3))

class PickPlaceUI(MDApp):

    def __init__(self, panda_app, display_region):
        super().__init__(panda_app=panda_app, display_region=display_region)
        self.screen = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.screen = Builder.load_string(PickPlace_panel_kv)
        return self.screen

    def on_start(self):
        self.screen.ids.btn1.bind(on_press = lambda _: open_scene(31))
        self.screen.ids.btn2.bind(on_press = lambda _: open_scene(13))
        self.screen.ids.btn3.bind(on_press = lambda _: open_scene(19))
        self.screen.ids.btn4.bind(on_press = lambda _: open_scene(0))
        self.screen.ids.btn5.bind(on_press = lambda _: open_scene(4))
        self.screen.ids.btn6.bind(on_press = lambda _: open_scene(4))
        self.screen.ids.btn7.bind(on_press = lambda _: open_scene(4))


class ECMUI(MDApp):

    def __init__(self, panda_app, display_region):
        super().__init__(panda_app=panda_app, display_region=display_region)
        self.screen = None

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.screen = Builder.load_string(ECM_panel_kv)
        return self.screen

    def on_start(self):
        self.screen.ids.btn1.bind(on_press = lambda _: open_scene(21))
        self.screen.ids.btn2.bind(on_press = lambda _: open_scene(23))
        self.screen.ids.btn3.bind(on_press = lambda _: open_scene(25))
        self.screen.ids.btn4.bind(on_press = lambda _: open_scene(27))
        self.screen.ids.btn5.bind(on_press = lambda _: open_scene(0))
        self.screen.ids.btn6.bind(on_press = lambda _: open_scene(1))


class StartPage(Scene):
    def __init__(self):
        super(StartPage, self).__init__()
        
    def on_start(self):
        self.ui_display_region = self.build_kivy_display_region(0, 1.0, 0, 1.0)
        self.kivy_ui = SelectionUI(
            self.app,
            self.ui_display_region
        )
        self.kivy_ui.run()
    
    def on_destroy(self):
        # !!! important
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)

class NeedlePage(Scene):
    def __init__(self):
        super(NeedlePage, self).__init__()
        
    def on_start(self):
        self.ui_display_region = self.build_kivy_display_region(0, 1.0, 0, 1.0)
        self.kivy_ui = NeedleUI(
            self.app,
            self.ui_display_region
        )
        self.kivy_ui.run()
    
    def on_destroy(self):
        # !!! important
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)

class PegPage(Scene):
    def __init__(self):
        super(PegPage, self).__init__()
        
    def on_start(self):
        self.ui_display_region = self.build_kivy_display_region(0, 1.0, 0, 1.0)
        self.kivy_ui = PegUI(
            self.app,
            self.ui_display_region
        )
        self.kivy_ui.run()
    
    def on_destroy(self):
        # !!! important
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)

class PickPlacePage(Scene):
    def __init__(self):
        super(PickPlacePage, self).__init__()
        
    def on_start(self):
        self.ui_display_region = self.build_kivy_display_region(0, 1.0, 0, 1.0)
        self.kivy_ui = PickPlaceUI(
            self.app,
            self.ui_display_region
        )
        self.kivy_ui.run()
    
    def on_destroy(self):
        # !!! important
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)

class ECMPage(Scene):
    def __init__(self):
        super(ECMPage, self).__init__()
        
    def on_start(self):
        self.ui_display_region = self.build_kivy_display_region(0, 1.0, 0, 1.0)
        self.kivy_ui = ECMUI(
            self.app,
            self.ui_display_region
        )
        self.kivy_ui.run()
    
    def on_destroy(self):
        # !!! important
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)

menu_bar_kv_haptic = '''MDBoxLayout:
    md_bg_color: (1, 0, 0, 0)
    # adaptive_height: True
    padding: "0dp", 0, 0, 0
    
    MDRectangleFlatIconButton:
        icon: "exit-to-app"
        id: btn1
        text: "Exit"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.primary_color
        size_hint: 0.25, 1.0
    MDRectangleFlatIconButton:
        icon: "head-lightbulb-outline"
        id: btn2
        text: "AI Assistant"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.bg_light
        size_hint: 0.25, 1.0
    MDRectangleFlatIconButton:
        icon: "chart-histogram"
        id: btn3
        text: "Evaluation"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.primary_color
        size_hint: 0.25, 1.0
    MDRectangleFlatIconButton:
        icon: "help-box"
        id: btn4
        text: "Switch to Demo"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.bg_light
        size_hint: 0.25, 1.0
'''
menu_bar_kv_RL = '''MDBoxLayout:
    md_bg_color: (1, 0, 0, 0)
    # adaptive_height: True
    padding: "0dp", 0, 0, 0
    
    MDRectangleFlatIconButton:
        icon: "exit-to-app"
        id: btn1
        text: "Exit"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.primary_color
        size_hint: 0.25, 1.0
    MDRectangleFlatIconButton:
        icon: "head-lightbulb-outline"
        id: btn2
        text: "AI Assistant"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.bg_light
        size_hint: 0.25, 1.0
    MDRectangleFlatIconButton:
        icon: "chart-histogram"
        id: btn3
        text: "Evaluation"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.primary_color
        size_hint: 0.25, 1.0
    MDRectangleFlatIconButton:
        icon: "help-box"
        id: btn4
        text: "Switch to Haptic Device Training"
        text_color: (1, 1, 1, 1)
        icon_color: (1, 1, 1, 1)
        md_bg_color: app.theme_cls.bg_light
        size_hint: 0.25, 1.0
'''
class MenuBarUI(MDApp):
    def __init__(self, panda_app, display_region,id = None):
        super().__init__(panda_app=panda_app, display_region=display_region)
        self.screen = None
        self.id = id
        self.ecm_list=[i for i in range(21,29)]
        self.fund_list = [31,32,5,6,9,10,29,30]
        self.basic_list=[7,8,11,12,15,16,17,18,13,14,19,20]
    def build(self):
        self.theme_cls.theme_style = "Dark"
        if self.id % 2 == 0:
            self.screen = Builder.load_string(menu_bar_kv_RL)
        else:
            self.screen = Builder.load_string(menu_bar_kv_haptic)
        return self.screen

    def on_start(self):
        # scene_menu = 1
        if self.id in self.ecm_list:
            self.screen.ids.btn1.bind(on_press = lambda _: open_scene(1))
        elif self.id in self.fund_list:
            self.screen.ids.btn1.bind(on_press = lambda _: open_scene(2))
        elif self.id in self.basic_list:
            self.screen.ids.btn1.bind(on_press = lambda _: open_scene(3))
        else:
            self.screen.ids.btn1.bind(on_press = lambda _: open_scene(0))
        if self.id % 2 ==0:
            self.screen.ids.btn4.bind(on_press = lambda _: (open_scene(0), open_scene(self.id-1)))
        else:
            self.screen.ids.btn4.bind(on_press = lambda _:(open_scene(0), open_scene(self.id+1)))
class SurgicalSimulatorBase(GymEnvScene):
    def __init__(self, env_type, env_params):
        super(SurgicalSimulatorBase, self).__init__(env_type, env_params)
    def before_simulation_step(self):
        pass

    def on_env_created(self):
        """Setup extrnal lights"""
        self.ecm_view_out = self.env._view_matrix

        table_pos = np.array(self.env.POSE_TABLE[0]) * self.env.SCALING

        # ambient light
        alight = AmbientLight('alight')
        alight.setColor((0.2, 0.2, 0.2, 1))
        alnp = self.world3d.attachNewNode(alight)
        self.world3d.setLight(alnp)

        # directional light
        dlight = DirectionalLight('dlight')
        dlight.setColor((0.4, 0.4, 0.25, 1))
        # dlight.setShadowCaster(True, app.configs.shadow_resolution, app.configs.shadow_resolution)
        dlnp = self.world3d.attachNewNode(dlight)
        dlnp.setPos(*(table_pos + np.array([1.0, 0.0, 15.0])))
        dlnp.lookAt(*table_pos)
        self.world3d.setLight(dlnp)

        # spotlight
        slight = Spotlight('slight')
        slight.setColor((0.5, 0.5, 0.5, 1.0))
        lens = PerspectiveLens()
        lens.setNearFar(0.5, 5)
        slight.setLens(lens)
        slight.setShadowCaster(True, app.configs.shadow_resolution, app.configs.shadow_resolution)
        slnp = self.world3d.attachNewNode(slight)
        slnp.setPos(*(table_pos + np.array([0, 0.0, 5.0])))
        slnp.lookAt(*(table_pos + np.array([0.6, 0, 1.0])))
        self.world3d.setLight(slnp)

    def on_start(self):
        self.ui_display_region = self.build_kivy_display_region(0, 1.0, 0, 0.061)
        self.kivy_ui = MenuBarUI(
            self.app,
            self.ui_display_region,
            self.id
        )
        self.kivy_ui.run()
    
    def on_destroy(self):
        # !!! important
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)

class MLP(nn.Module):
    def __init__(self, in_dim, out_dim, hidden_dim=256):
        super().__init__()

        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, out_dim), 
        )

    def forward(self, input):
        return self.mlp(input)


class DeterministicActor(nn.Module):
    def __init__(self, dimo, dimg, dima, hidden_dim=256):
        super().__init__()

        self.trunk = MLP(
            in_dim=dimo+dimg,
            out_dim=dima,
            hidden_dim=hidden_dim
        )

    def forward(self, obs):
        a = self.trunk(obs)
        return torch.tanh(a)

class Normalizer:
    def __init__(self, size, eps=1e-2, default_clip_range=np.inf):
        self.size = size
        self.eps = eps
        self.default_clip_range = default_clip_range
        # some local information
        self.total_sum = np.zeros(self.size, np.float32)
        self.total_sumsq = np.zeros(self.size, np.float32)
        self.total_count = np.zeros(1, np.float32)
        # get the mean and std
        self.mean = np.zeros(self.size, np.float32)
        self.std = np.ones(self.size, np.float32)
    
    # update the parameters of the normalizer
    def update(self, v):
        v = v.reshape(-1, self.size)
        # do the computing
        self.total_sum += v.sum(axis=0)
        self.total_sumsq += (np.square(v)).sum(axis=0)
        self.total_count[0] += v.shape[0]

    def recompute_stats(self):
        # calculate the new mean and std
        self.mean = self.total_sum / self.total_count
        self.std = np.sqrt(np.maximum(np.square(self.eps), (self.total_sumsq / self.total_count) - np.square(self.total_sum / self.total_count)))

    # normalize the observation
    def normalize(self, v, clip_range=None):
        if clip_range is None:
            clip_range = self.default_clip_range
        return np.clip((v - self.mean) / (self.std), -clip_range, clip_range)


class SurgicalSimulator(SurgicalSimulatorBase):
    def __init__(self, env_type, env_params,id=None,demo=None):
        super(SurgicalSimulator, self).__init__(env_type, env_params)
        self.id = id
        initTouch_right()
        startScheduler()
        if env_type.ACTION_SIZE != 3 and env_type.ACTION_SIZE != 1:
            self.psm1_action = np.zeros(env_type.ACTION_SIZE)
            self.psm1_action[4] = 0.5

            self.app.accept('w-up', self.setPsmAction, [2, 0])
            self.app.accept('w-repeat', self.addPsmAction, [2, 0.01])
            self.app.accept('s-up', self.setPsmAction, [2, 0])
            self.app.accept('s-repeat', self.addPsmAction, [2, -0.01])
            self.app.accept('d-up', self.setPsmAction, [1, 0])
            self.app.accept('d-repeat', self.addPsmAction, [1, 0.01])
            self.app.accept('a-up', self.setPsmAction, [1, 0])
            self.app.accept('a-repeat', self.addPsmAction, [1, -0.01])
            self.app.accept('q-up', self.setPsmAction, [0, 0])
            self.app.accept('q-repeat', self.addPsmAction, [0, 0.01])
            self.app.accept('e-up', self.setPsmAction, [0, 0])
            self.app.accept('e-repeat', self.addPsmAction, [0, -0.01])
            self.app.accept('space-up', self.setPsmAction, [4, 1.0])
            self.app.accept('space-repeat', self.setPsmAction, [4, -0.5])

        self.ecm_view = 0
        self.ecm_view_out = None
        self.demo = demo
        self.start_time = time.time()
        exempt_l = [i for i in range(21,23)]
        if self.id not in exempt_l:
            self.toggleEcmView()
        self.has_load_policy = False

        self.ecm_action = np.zeros(env_type.ACTION_ECM_SIZE)
        if env_type.ACTION_ECM_SIZE == 1:
                self.app.accept('1-up', self.setEcmAction, [0, 0])
                self.app.accept('1-repeat', self.addEcmAction, [0, 0.2])
                self.app.accept('3-up', self.setEcmAction, [0, 0])
                self.app.accept('3-repeat', self.addEcmAction, [0, -0.2])
        else:
            self.app.accept('5-up', self.setEcmAction, [2, 0])
            self.app.accept('5-repeat', self.addEcmAction, [2, 0.2])
            self.app.accept('2-up', self.setEcmAction, [2, 0])
            self.app.accept('2-repeat', self.addEcmAction, [2, -0.2])
            self.app.accept('6-up', self.setEcmAction, [1, 0])
            self.app.accept('6-repeat', self.addEcmAction, [1, 0.2])
            self.app.accept('4-up', self.setEcmAction, [1, 0])
            self.app.accept('4-repeat', self.addEcmAction, [1, -0.2])
            self.app.accept('1-up', self.setEcmAction, [0, 0])
            self.app.accept('1-repeat', self.addEcmAction, [0, 0.2])
            self.app.accept('3-up', self.setEcmAction, [0, 0])
            self.app.accept('3-repeat', self.addEcmAction, [0, -0.2])
            self.app.accept('m-up', self.toggleEcmView)
            self.app.accept('r-up', self.resetEcmFlag)

    def _step_simulation_task(self, task):
        """Step simulation
        """
        if self.demo == None:
            # print(f"scene id:{self.id}")
            if task.time - self.time > 1 / 240.0:
                self.before_simulation_step()

                # Step simulation
                p.stepSimulation()
                self.after_simulation_step()

                # Call trigger update scene (if necessary) and draw methods
                p.getCameraImage(
                    width=1, height=1,
                    viewMatrix=self.env._view_matrix,
                    projectionMatrix=self.env._proj_matrix)
                p.setGravity(0,0,-10.0)
                # print(f"ecm view out matrix:{self.ecm_view_out}")
                self.time = task.time
        else:
            if time.time() - self.time > 1/240:
                self.before_simulation_step()

                # Step simulation
                #pb.stepSimulation()
                # self._duration = 0.1 # needle 
                self._duration = 0.1
                step(self._duration)

                self.after_simulation_step()

                # Call trigger update scene (if necessary) and draw methods
                p.getCameraImage(
                    width=1, height=1,
                    viewMatrix=self.env._view_matrix,
                    projectionMatrix=self.env._proj_matrix)
                p.setGravity(0,0,-10.0)

                self.time = time.time()
                # print(f"current time: {self.time}")
                # print(f"current task time: {task.time}")

                # if time.time()-self.start_time > (self.itr + 1) * time_size:
                obs = self.env._get_obs()
                obs = self.env._get_obs()['achieved_goal'] if isinstance(obs, dict) else None
                # print(f"waypoints: {self.env._waypoints}")
                success = self.env._is_success(obs,self.env._sample_goal()) if obs is not None else False
                # print(f"success: {success}")
                wait_list=[12,30]
                if (self.id not in wait_list and success) or time.time()-self.start_time > 10:   
                    # if self.cnt>=6: 
                    #     self.kivy_ui.stop()
                    #     self.app.win.removeDisplayRegion(self.ui_display_region)
                    # self.before_simulation_step()
                    # self._duration = 0.2
                    # step(self._duration)
                    # self.after_simulation_step()
                    
                    open_scene(0)
                    # print(f"xxxx current time:{time.time()}")
                    open_scene(self.id)
                    exempt_l = [i for i in range(21,23)]
                    if self.id not in exempt_l:
                        self.toggleEcmView()
                    # self.cnt+=1
                    return 
                    # self.start_time=time.time()
                    # self.toggleEcmView()
                    # self.itr += 1
                        
        return Task.cont

    def load_policy(self, obs, env):
        steps = str(300000)
        if self.id == 8:
            model_file = './peg_transfer_model'
        if self.id == 6:
            model_file = './needle_pick_model'

        actor_params = os.path.join(model_file, 'actor_' + steps + '.pt')
        actor_params = torch.load(actor_params)

        dim_o = obs['observation'].shape[0]
        dim_g = obs['desired_goal'].shape[0]
        dim_a = env.action_space.shape[0]
        actor = DeterministicActor(
            dim_o, dim_g, dim_a, 256
        )

        actor.load_state_dict(actor_params)

        g_norm = Normalizer(dim_g)
        g_norm_stat = np.load(os.path.join(model_file, 'g_norm_' + steps + '_stat.npy'), allow_pickle=True).item()
        g_norm.mean = g_norm_stat['mean']
        g_norm.std = g_norm_stat['std']

        o_norm = Normalizer(dim_o)
        o_norm_stat = np.load(os.path.join(model_file, 'o_norm_' + steps + '_stat.npy'), allow_pickle=True).item()
        o_norm.mean = o_norm_stat['mean']
        o_norm.std = o_norm_stat['std']

        return actor, o_norm, g_norm

    def _preproc_inputs(self, o, g, o_norm, g_norm):
        o_norm = o_norm.normalize(o)
        g_norm = g_norm.normalize(g)
 
        inputs = np.concatenate([o_norm, g_norm])
        inputs = torch.tensor(inputs, dtype=torch.float32).unsqueeze(0)
        return inputs

    def before_simulation_step(self):
        if (self.id == 8 or self.id == 6) and not self.has_load_policy:
            obs = self.env._get_obs()
            self.actor, self.o_norm,self.g_norm = self.load_policy(obs,self.env)
            self.has_load_policy = True

        self.ecm_action = np.zeros(self.ecm_action.shape)
        retrived_action = np.array([0, 0, 0, 0, 0], dtype = np.float32)
        getDeviceAction_right(retrived_action)
        print(f"retrived action is: {retrived_action}")
        if self.demo:
            obs = self.env._get_obs()
            action = self.env.get_oracle_action(obs)

        if self.env.ACTION_SIZE != 3 and self.env.ACTION_SIZE != 1:

            # haptic right
            # retrived_action-> x,y,z, angle, buttonState(0,1,2)
            if retrived_action[4] == 2:
                self.psm1_action[0] = 0
                self.psm1_action[1] = 0
                self.psm1_action[2] = 0
                self.psm1_action[3] = 0            
         
            else:
                self.psm1_action[0] = retrived_action[2]*0.9
                self.psm1_action[1] = retrived_action[0]*0.9
                self.psm1_action[2] = retrived_action[1]*0.9
                self.psm1_action[3] = -retrived_action[3]/math.pi*180*0.5

            if retrived_action[4] == 0:
                self.psm1_action[4] = 1
            if retrived_action[4] == 1:
                self.psm1_action[4] = -0.5
                
            if retrived_action[4] == 3:
                self.psm1_action[0] = 0
                self.psm1_action[1] = 0
                self.psm1_action[2] = 0
                self.psm1_action[3] = 0 

            # print(f"len of retrieved action:{len(retrived_action)}")
            if self.demo:
                if self.id ==8:
                    obs = self.env._get_obs()
                    o, g = obs['observation'], obs['desired_goal']
                    input_tensor = self._preproc_inputs(o, g, self.o_norm, self.g_norm)
                    action = self.actor(input_tensor).data.numpy().flatten()
                    # print(f"retrieved action is: {self.psm1_action}")
                    self.psm1_action = action
                    self.env._set_action(self.psm1_action)
                else:
                    obs = self.env._get_obs()
                    action = self.env.get_oracle_action(obs)
                    self.psm1_action = action
                    self.env._set_action(self.psm1_action)
                    self.env._step_callback()
            else:
                self.env._set_action(self.psm1_action)
                self.env._step_callback()
        if retrived_action[4] == 3 and self.env.ACTION_ECM_SIZE == 3:  
            self.ecm_action[0] = -retrived_action[0]*0.2
            self.ecm_action[1] = -retrived_action[1]*0.2
            self.ecm_action[2] = retrived_action[2]*0.2

        if retrived_action[4] == 3 and self.env.ACTION_ECM_SIZE == 1:
            self.ecm_action[0] = -retrived_action[3]/math.pi*180*0.5

        #active track
        if self.id == 27 or self.id == 28:
            self.env._step_callback()

        # self.env._set_action(self.ecm_action)
        if self.demo and (self.env.ACTION_ECM_SIZE == 3 or self.env.ACTION_ECM_SIZE == 1):
            self.ecm_action = action
            self.env._set_action(self.ecm_action)
        if self.demo is None:
            if self.env.ACTION_ECM_SIZE == 1:
                self.env._set_action(self.ecm_action)
            else:
                self.env._set_action_ecm(self.ecm_action)
            
            
        self.env.ecm.render_image()
        # _,_,rgb,_,_ = p.getCameraImage(
        #             width=100, height=100,
        #             viewMatrix=self.env._view_matrix,
        #             projectionMatrix=self.env._proj_matrix
        #             )
        # rgb_array = np.array(rgb, dtype=np.uint8)
        # if len(rgb_array)>0:
        #     rgb_array = np.reshape(rgb_array, (100, 100, 4))

        #     rgb_array = rgb_array[:, :, :3]

        #     imageio.imwrite('test.png',rgb_array)
        if self.ecm_view:
            self.env._view_matrix = self.env.ecm.view_matrix
        else:
            self.env._view_matrix = self.ecm_view_out

    def setPsmAction(self, dim, val):
        self.psm1_action[dim] = val
        
    def addPsmAction(self, dim, incre):
        self.psm1_action[dim] += incre

    def addEcmAction(self, dim, incre):
        self.ecm_action[dim] += incre

    def setEcmAction(self, dim, val):
        self.ecm_action[dim] = val
    def resetEcmFlag(self):
        # print("reset enter")
        self.env._reset_ecm_pos()
    def toggleEcmView(self):
        self.ecm_view = not self.ecm_view

    def on_destroy(self):
        # !!! important
        stopScheduler()
        closeTouch_right()
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)


class SurgicalSimulatorBimanual(SurgicalSimulatorBase):
    def __init__(self, env_type, env_params, jaw_states=[1.0, 1.0],id=None,demo=None):
        super(SurgicalSimulatorBimanual, self).__init__(env_type, env_params)
        self.network = Net()
        self.console = Console(self.network)

        self.id=id
        self.demo = demo
        self.closed=True
        self.start_time = time.time()

        self.psm1_action = np.zeros(env_type.ACTION_SIZE // 2)
        self.psm1_action[4] = jaw_states[0]

        self.psm2_action = np.zeros(env_type.ACTION_SIZE // 2)
        self.psm2_action[4] = jaw_states[1]

        self.last_gripper_0 = 0
        self.last_gripper_1 = 0

        p = self.network.P_enabled
        d = self.network.D_enabled
        c = self.network.C_enabled
        m = self.network.model_str
        n = self.network.trial_num

        self.logger1 = DataLogger("robot_sim_data", p, d, c, m, n, str(user_num))
        self.logger2 = DataLogger("robot_command_data", p, d, c, m, n, str(user_num))
        self.obs = OBSController("localhost", 4455, "rYIh2EvZGlDxDV0L")

        self.app.accept('w-up', self.setPsmAction1, [2, 0])
        self.app.accept('w-repeat', self.addPsmAction1, [2, 0.01])
        self.app.accept('s-up', self.setPsmAction1, [2, 0])
        self.app.accept('s-repeat', self.addPsmAction1, [2, -0.01])
        self.app.accept('d-up', self.setPsmAction1, [1, 0])
        self.app.accept('d-repeat', self.addPsmAction1, [1, 0.01])
        self.app.accept('a-up', self.setPsmAction1, [1, 0])
        self.app.accept('a-repeat', self.addPsmAction1, [1, -0.01])
        self.app.accept('q-up', self.setPsmAction1, [0, 0])
        self.app.accept('q-repeat', self.addPsmAction1, [0, 0.01])
        self.app.accept('e-up', self.setPsmAction1, [0, 0])
        self.app.accept('e-repeat', self.addPsmAction1, [0, -0.01])
        self.app.accept('c-up', self.setPsmAction1, [4, 1.0])
        self.app.accept('c-repeat', self.setPsmAction1, [4, -0.5])

        self.app.accept('i-up', self.setPsmAction2, [2, 0])
        self.app.accept('i-repeat', self.addPsmAction2, [2, 0.01])
        self.app.accept('k-up', self.setPsmAction2, [2, 0])
        self.app.accept('k-repeat', self.addPsmAction2, [2, -0.01])
        self.app.accept('l-up', self.setPsmAction2, [1, 0])
        self.app.accept('l-repeat', self.addPsmAction2, [1, 0.01])
        self.app.accept('j-up', self.setPsmAction2, [1, 0])
        self.app.accept('j-repeat', self.addPsmAction2, [1, -0.01])
        self.app.accept('u-up', self.setPsmAction2, [0, 0])
        self.app.accept('u-repeat', self.addPsmAction2, [0, 0.01])
        self.app.accept('o-up', self.setPsmAction2, [0, 0])
        self.app.accept('o-repeat', self.addPsmAction2, [0, -0.01])
        self.app.accept('n-up', self.setPsmAction2, [4, 1.0])
        self.app.accept('n-repeat', self.setPsmAction2, [4, -0.5])

        self.ecm_view = 0
        self.ecm_view_out = None
        exempt_l = [i for i in range(21,23)]
        if self.id not in exempt_l:
            self.toggleEcmView()
        self.ecm_action = np.zeros(env_type.ACTION_ECM_SIZE)
        self.app.accept('5-up', self.setEcmAction, [2, 0])
        self.app.accept('5-repeat', self.addEcmAction, [2, 0.2])
        self.app.accept('2-up', self.setEcmAction, [2, 0])
        self.app.accept('2-repeat', self.addEcmAction, [2, -0.2])
        self.app.accept('6-up', self.setEcmAction, [1, 0])
        self.app.accept('6-repeat', self.addEcmAction, [1, 0.2])
        self.app.accept('4-up', self.setEcmAction, [1, 0])
        self.app.accept('4-repeat', self.addEcmAction, [1, -0.2])
        self.app.accept('1-up', self.setEcmAction, [0, 0])
        self.app.accept('1-repeat', self.addEcmAction, [0, 0.2])
        self.app.accept('3-up', self.setEcmAction, [0, 0])
        self.app.accept('3-repeat', self.addEcmAction, [0, -0.2])
        self.app.accept('m-up', self.toggleEcmView)
        self.app.accept('r-up', self.resetEcmFlag)

        self.network.start()
        self.console.start()
        self.video_recording = False
        self.obs.connect()
        #self.obs.start_recording()

          
        self.subtask = "Pick"
        self.subtask1 = False
        self.subtask2 = False
        self.subtask3 = False
        self.subtask4 = False
        self.subtask5 = False
        self.subtask6 = False
        self.subtask7 = False
        self.color = "Red"

    def get_peg_pose(self, color):
        peg_id = None
        if color == "Red":
            peg_id = self.env.obj_ids['rigid'][0]
        elif color == "Green":
            peg_id = self.env.obj_ids['rigid'][1]
        elif color == "Blue":
            peg_id = self.env.obj_ids['rigid'][2]
        elif color == "Magenta":
            peg_id = self.env.obj_ids['rigid'][3]
        elif color == "Yellow":
            peg_id = self.env.obj_ids['rigid'][4]
        elif color == "Cyan":
            peg_id = self.env.obj_ids['rigid'][5]
        pos, orn = get_link_pose(peg_id, 0)
        return pos, orn

    def move_z(self, target_pos):
        cur_pos = self.env.psm1.pose_rcm2world(self.env.psm1.get_current_position(), 'tuple')[0]
        # print("target z position:", target_pos[2])
        #print("current z position:", cur_pos)
        delta_z = target_pos[2] - cur_pos[2]
        if abs(delta_z) > 0.1:
            return np.array([0.0, 0.0, np.sign(delta_z)*0.05])
        else:
            return np.zeros(3)
    
    def move_x(self, target_pos):
        cur_pos = self.env.psm1.pose_rcm2world(self.env.psm1.get_current_position(), 'tuple')[0]
        # print("target z position:", target_pos[2])
        #print("current z position:", cur_pos)
        delta_x = target_pos[0] - cur_pos[0]
        print("delta x:", delta_x)
        if abs(delta_x) > 0.01:
            return np.array([np.sign(delta_x)*0.05, 0.0, 0.0])
        else:
            return np.zeros(3)
    
    def _step_simulation_task(self, task):
        """Step simulation
        """
        if self.demo == None:
            # print(f"scene id:{self.id}")
            if task.time - self.time > 1 / 240.0:
                self.before_simulation_step()

                # Step simulation
                p.stepSimulation()
                self.after_simulation_step()

                # Call trigger update scene (if necessary) and draw methods
                (width, height, rgb_pixels, depth_pixels, seg_pixels) = p.getCameraImage(
                    width=256, height=256,
                    viewMatrix=self.env._view_matrix,
                    projectionMatrix=self.env._proj_matrix)
                p.setGravity(0,0,-10.0)
                #print(width, height, rgb_pixels.shape, depth_pixels.shape, seg_pixels.shape)
                self.time = task.time

                # --- Get PSM poses here ---
                psm1_pose = self.env.psm1.get_current_position()
                pos1 = psm1_pose[:3, 3]
                rot1 = R.from_matrix(psm1_pose[:3, :3]).as_euler('xyz')
                # print(f"psm1 rot: {rot1[-1]}")
                # print(f"psm1 pose: {R.from_matrix(psm1_pose[:3, :3]).as_euler('xyz', degrees=True)}")

                psm2_pose = self.env.psm2.get_current_position()
                pos2 = psm2_pose[:3, 3]
                rot2 = R.from_matrix(psm2_pose[:3, :3]).as_euler('xyz')
                #print(f"psm2 rot: {rot2[-1]}")

                # pos, orn = self.get_peg_pose(self.color)
                # #print(f"{pos}")
                # orn = p.getEulerFromQuaternion(orn)
                # print(f"peg orn: {orn}")

                if self.video_recording == False:
                    self.video_recording = True
                    self.obs.start_recording()
                
                if self.video_recording == True:
                    self.logger1.log_data_sim(time.time(), self.console.sequence_num, pos2, rot2, pos1, rot1)
                
                # if self.video_recording:
                #     rgb_array = np.array(rgb_pixels, dtype=np.uint8).reshape((height, width, 4))
                #     img = rgb_array[:, :, :3][:, :, ::-1]
                #     print("img type:", type(img), "shape:", getattr(img, "shape", None), "dtype:", getattr(img, "dtype", None))
                #     self.images.append(img)     
        else:
            if time.time() - self.time > 1/240:
                self.before_simulation_step()

                # Step simulation
                #pb.stepSimulation()
                # self._duration = 0.1 # needle 
                self._duration = 0.1
                step(self._duration)

                self.after_simulation_step()

                # Call trigger update scene (if necessary) and draw methods
                p.getCameraImage(
                    width=1, height=1,
                    viewMatrix=self.env._view_matrix,
                    projectionMatrix=self.env._proj_matrix)
                p.setGravity(0,0,-10.0)

                self.time = time.time()
                # print(f"current time: {self.time}")
                # print(f"current task time: {task.time}")

                # if time.time()-self.start_time > (self.itr + 1) * time_size:
                obs = self.env._get_obs()
                obs = self.env._get_obs()['achieved_goal'] if isinstance(obs, dict) else None
                # success = self.env._is_success(obs,self.env._sample_goal()) if obs is not None else False
                if  time.time()-self.start_time > 18:   
                    # if self.cnt>=6: 
                    #     self.kivy_ui.stop()
                    #     self.app.win.removeDisplayRegion(self.ui_display_region)

                    open_scene(0)
                    print(f"xxxx current time:{time.time()}")
                    open_scene(self.id)
                    exempt_l = [i for i in range(21,23)]
                    if self.id not in exempt_l:
                        self.toggleEcmView()
                    # self.cnt+=1
                    return 
                    # self.start_time=time.time()
                    # self.toggleEcmView()
                    # self.itr += 1
                        
        return Task.cont


    def before_simulation_step(self):
        self.console.set_event()
        commands = self.console.get_transformed_data()
        target_pos = self.get_peg_pose(self.color)[0]
        goal_pos = np.array([2.6, -0.16, 3.77])
        target_yaw = 0.6
        target_yaw_task3 = -0.2
        target_z = 3.77
        target_y_task3 = 0
        target_x_task3_2 = 2.64
        target_y_task3_2 = -.01
        target_z_task3 = 3.8
        target_z_task4 = 3.73
        target_z_task7 = 3.65
        action_pos_0 = np.zeros(3)
        action_rot_0 = np.zeros(3)
        action_pos_1 = np.zeros(3)
        action_rot_1 = np.zeros(3)
        gripper_0 = 0.0
        gripper_1 = 0.0
        step_size = 0.08
        if not self.subtask1:
            target_pos = np.array([target_pos[0]+0.06, target_pos[1]+0.009, target_pos[2]])
            cur_yaw = self.env.psm1.get_current_joint_position()[3]
            cur_pos = self.env.psm1.pose_rcm2world(self.env.psm1.get_current_position(), 'tuple')[0]
            delta_x = target_pos[0] - cur_pos[0]
            delta_y = target_pos[1] - cur_pos[1]
            delta_z = target_pos[2] - cur_pos[2]
            delta_yaw = target_yaw - cur_yaw
            print("Move right arm to goal position:", delta_x, delta_y, delta_z)
            if abs(delta_z) > 0.065:
                action_pos_1[2] = np.sign(delta_z)*step_size
            if abs(delta_x) > 0.02:
                action_pos_1[0] = np.sign(delta_x)*step_size
            if abs(delta_y) > 0.02:
                action_pos_1[1] = np.sign(delta_y)*step_size
            if abs(delta_yaw) > 0.1:
                action_rot_1[2] = -np.sign(delta_yaw)*0.1
            if abs(delta_x) <= 0.02 and abs(delta_y) <= 0.02 and abs(delta_z) <= 0.065 and abs(delta_yaw) <= 0.1: 
                self.subtask1 = True
        if self.subtask1 and not self.subtask2:
            gripper_1 = -1.0
            cur_z = self.env.psm1.pose_rcm2world(self.env.psm1.get_current_position(), 'tuple')[0][2]
            print("Current z for lift:", cur_z)
            delta_z = target_z - cur_z
            #print("delta z for lift:", delta_z)
            if delta_z > 0.03:
                action_pos_1[2] = np.sign(delta_z)*step_size
            if delta_z <= 0.03:
                self.subtask2 = True
        if self.subtask2 and not self.subtask3:
            gripper_1 = -1.0
            cur_yaw = self.env.psm2.get_current_joint_position()[3]
            cur_y = self.env.psm1.pose_rcm2world(self.env.psm1.get_current_position(), 'tuple')[0][1]
            cur_x_2 = self.env.psm2.pose_rcm2world(self.env.psm2.get_current_position(), 'tuple')[0][0]
            cur_y_2 = self.env.psm2.pose_rcm2world(self.env.psm2.get_current_position(), 'tuple')[0][1]
            cur_z_2 = self.env.psm2.pose_rcm2world(self.env.psm2.get_current_position(), 'tuple')[0][2]
            delta_y = target_y_task3 - cur_y
            delta_x_2 = target_x_task3_2 - cur_x_2
            delta_y_2 = target_y_task3_2 - cur_y_2
            delta_z_2 = target_z_task3 - cur_z_2
            delta_yaw = target_yaw_task3 - cur_yaw
            print("Move right arm to left arm:", delta_x_2, delta_y_2, delta_z_2)
            if abs(delta_y) > 0.02:
                action_pos_1[1] = np.sign(delta_y)*step_size
            if abs(delta_x_2) > 0.02:
                action_pos_0[0] = np.sign(delta_x_2)*step_size
            if abs(delta_y_2) > 0.01:
                action_pos_0[1] = np.sign(delta_y_2)*step_size
            if abs(delta_z_2) > 0.02:
                action_pos_0[2] = np.sign(delta_z_2)*step_size
            if abs(delta_yaw) > 0.1:
                action_rot_0[2] = -np.sign(delta_yaw)*0.1
            if abs(delta_y) <= 0.02 and abs(delta_y_2) <= 0.01 and abs(delta_z_2) <= 0.02 and abs(delta_x_2) <= 0.02 and abs(delta_yaw) <= 0.1: 
                self.subtask3 = True
        if self.subtask3 and not self.subtask4:
           gripper_1 = -1.0
           cur_z_2 = self.env.psm2.pose_rcm2world(self.env.psm2.get_current_position(), 'tuple')[0][2]
           delta_z_2 = target_z_task4 - cur_z_2
           print("Lower the left arm Z axis for grasp:", delta_z_2)
           if abs(delta_z_2) > 0.002:
               action_pos_0[2] = np.sign(delta_z_2)*step_size
           if abs(delta_z_2) <= 0.002:
               gripper_0 = -1.0
               self.subtask4 = True
               time.sleep(0.6)

        if self.subtask4 and not self.subtask5:
            gripper_0 = -1.0
            cur_z = self.env.psm1.pose_rcm2world(self.env.psm1.get_current_position(), 'tuple')[0][2]
            print("Raise right arm the Z axis:", cur_z)
            delta_z = target_z_task3 - cur_z
            if abs(delta_z) > 0.02:
                action_pos_1[2] = np.sign(delta_z)*step_size
            if abs(delta_z) <= 0.02:
                self.subtask5 = True
        
        if self.subtask5 and not self.subtask6:
           gripper_0 = -1.0 
           cur_pos = self.env.psm2.pose_rcm2world(self.env.psm2.get_current_position(), 'tuple')[0]
           delta_x = goal_pos[0] - cur_pos[0]
           delta_y = goal_pos[1] - cur_pos[1]
           delta_z = goal_pos[2] - cur_pos[2]
           print("Move left arm to goal position:", delta_x, delta_y, delta_z)
           if abs(delta_x) > 0.01:
               action_pos_0[0] = np.sign(delta_x)*step_size
           if abs(delta_y) > 0.01:
               action_pos_0[1] = np.sign(delta_y)*step_size
           if abs(delta_z) > 0.01:
               action_pos_0[2] = np.sign(delta_z)*step_size
           if abs(delta_x) <= 0.01 and abs(delta_y) <= 0.01 and abs(delta_z) <= 0.01:
               self.subtask6 = True

        if self.subtask6 and not self.subtask7:
            gripper_0 = -1.0
            cur_z_2 = self.env.psm2.pose_rcm2world(self.env.psm2.get_current_position(), 'tuple')[0][2]
            delta_z_2 = target_z_task7 - cur_z_2
            print("Lower the left arm Z axis:", delta_z_2)
            if abs(delta_z_2) > 0.002:
                action_pos_0[2] = np.sign(delta_z_2)*step_size
            if abs(delta_z_2) <= 0.002:
                gripper_1 = 1.0
                self.subtask7 = True

        if commands:
            delta_pos_0 = action_pos_0
            delta_rot_0 = action_rot_0
            # if commands[-2] < -0.7:
            #     gripper_0 = -1.0
            # else:
            #     gripper_0 = 1.0

            delta_pos_1 = action_pos_1
            delta_rot_1 = action_rot_1
            # if commands[-1] < -0.7:
            #     gripper_1 = -1.0
            # else:
            #     gripper_1 = 1.0
            self.last_gripper_0 = gripper_0
            self.last_gripper_1 = gripper_1

            yaw_1 = self.env.psm1.get_current_joint_position()[3]
            yaw_0 = self.env.psm2.get_current_joint_position()[3]
            if yaw_1 - delta_rot_1[2] > 3.14 or yaw_1 - delta_rot_1[2] < -3.14:
                delta_rot_1[2] = 0
            if yaw_0 - delta_rot_0[2] > 3.14 or yaw_0 - delta_rot_0[2] < -3.14:
                delta_rot_0[2] = 0

            self.psm1_action = np.concatenate([delta_pos_0, np.array([delta_rot_0[2]]), np.array([gripper_0])])
            self.psm2_action = np.concatenate([delta_pos_1, np.array([delta_rot_1[2]]), np.array([gripper_1])])
            
            self.logger2.log_data_sampled(time.time(), self.console.sequence_num, delta_pos_0, delta_rot_0, delta_pos_1, delta_rot_1, self.psm1_action[4], self.psm2_action[4])
        else:
            self.psm1_action = np.zeros(5)
            self.psm2_action = np.zeros(5)
            self.psm1_action[4] = self.last_gripper_0
            self.psm2_action[4] = self.last_gripper_1
        
        #print(self.env.obj_id)
        #print(p.getBaseVelocity(self.env.obj_id))

        self.env._set_action(np.concatenate([self.psm2_action, self.psm1_action], axis=-1))
        self.env._step_callback()

        # self.env._set_action(self.ecm_action)
        self.env._set_action_ecm(self.ecm_action)
        self.env.ecm.render_image()

        if self.ecm_view:
            self.env._view_matrix = self.env.ecm.view_matrix
        else:
            self.env._view_matrix = self.ecm_view_out

    def generate_video(self):
        if self.video_recording and self.images:
            self.video_recording = False
            video_name = "video_peg_transfer.mp4"
            imageio.imwrite('test_frame.png', self.images[-1])
            writer = imageio.get_writer(os.path.join(os.path.dirname(__file__), video_name), fps=20)
            for img in self.images:
                writer.append_data(img)
            writer.close()
            print("Saved video at:", os.path.join(os.path.dirname(__file__), video_name))

    def setPsmAction1(self, dim, val):
        self.psm1_action[dim] = val
        
    def addPsmAction1(self, dim, incre):
        self.psm1_action[dim] += incre

    def setPsmAction2(self, dim, val):
        self.psm2_action[dim] = val
        
    def addPsmAction2(self, dim, incre):
        self.psm2_action[dim] += incre

    def addEcmAction(self, dim, incre):
        self.ecm_action[dim] += incre

    def setEcmAction(self, dim, val):
        self.ecm_action[dim] = val
    def resetEcmFlag(self):
        # print("reset enter")
        self.env._reset_ecm_pos()
    def toggleEcmView(self):
        self.ecm_view = not self.ecm_view

    def on_destroy(self):
        # !!! important
        self.console.close()
        self.network.stop()
        #self.generate_video()
        self.obs.stop_recording()
        self.logger1.close()
        self.logger2.close()
        self.kivy_ui.stop()
        self.app.win.removeDisplayRegion(self.ui_display_region)


# ecm steoro size 1024x768
app_cfg = ApplicationConfig(window_width=1850, window_height=1020)
app = Application(app_cfg)
open_scene(0)
app.run()