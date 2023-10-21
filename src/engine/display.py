import os
import time
import multiprocessing as mp
import pygame as pg
import queue
from pygame.locals import *

class Canvas(object):
    DefaultResolution = (1920, 1080)
    screen = None
    
    def __init__(self, frame_rate=60):
        self.frame_rate = frame_rate
        self.init_pygame()
        
    def init_display_driver(self):
        pg.init()
        disp_no = os.getenv("DISPLAY")
        if disp_no:
            print("I'm running under X display = {0}".format(disp_no))
        #drivers = ['fbcon', 'directfb', 'svgalib', 'x11']
        drivers = ['X11', 'dga', 'ggi','vgl','directfb', 'fbcon', 'svgalib']
        found = False
        for driver in drivers:
            print(driver)
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)
            try:
                pg.display.init()
            except pg.error as err:
                print(err)
                print('Driver: {0} failed.'.format(driver))
                continue
            found = True
            break
        if not found:
            raise Exception('No suitable video driver found!')
        modes = pg.display.list_modes()
        print(modes)
        #pg.display.set_mode(modes[0])
        #pg.display.set_mode(self.DefaultResolution, pg.RESIZABLE)
        pg.display.set_mode(self.DefaultResolution, DOUBLEBUF|OPENGL)
        pg.display.toggle_fullscreen()
        
    def init_pygame(self):
        self.init_display_driver()
        self.size = (pg.display.Info().current_w, pg.display.Info().current_h)
        msg = "Framebuffer size: %d x %d" % (self.size[0], self.size[1])
        print(msg)
        self.screen = pg.display.set_mode(self.size, pg.FULLSCREEN)
        self.screen.fill((0, 0, 0))        
        pg.font.init()
        pg.display.update()
        pg.mouse.set_visible(False)
        self.clock = pg.time.Clock()

    def loop(self):
        self.clock.tick(self.frame_rate)
        pg.display.update()
        fps = self.clock.get_fps()

class DisplayController(object):
    def __init__(self, canvas):
        self.canvas = canvas
        self.font = pg.font.Font(None, 240)
        self.buffer = pg.Surface(self.canvas.screen.get_size())
        self.buffer.fill(pg.Color("black"))
        self.refresh = None

    def display_image(self, fn_img):
        img = pg.image.load(fn_img)
        img = pg.transform.scale(img, self.canvas.size)
        screen_rect = self.canvas.screen.get_rect()
        rect = img.get_rect(center=(screen_rect.centerx, screen_rect.centery))
        self.buffer.fill(pg.Color("red"))
        self.buffer.blit(img, rect)

    def display_text(self, text):
        surface = self.font.render(text, True, pg.Color("dodgerblue"))
        screen_rect = self.canvas.screen.get_rect()
        rect = surface.get_rect(center=(screen_rect.centerx, screen_rect.centery))
        self.buffer.fill(pg.Color("black"))
        self.buffer.blit(surface, rect)

    def draw(self):
        if self.refresh:
            self.refresh()
            self.refresh = None
        rect = self.buffer.get_rect()
        self.canvas.screen.blit(self.buffer, rect)

class DisplayEngine(mp.Process):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = False
        self.display_queue = mp.Queue()

    def run(self):
        self.canvas = Canvas()
        self.control = DisplayController(self.canvas)
        try:
            self.running = True
            while self.running:
                try:
                    item = self.display_queue.get(False)
                    if item[0] == 'display_text':
                        self.control.display_text(item[1])
                    elif item[0] == 'display_image':
                        self.control.display_image(item[1])
                    else:
                        raise ValueError(item[0])
                except queue.Empty:
                    pass
                self.control.draw()
                self.canvas.loop()
        finally:
            pg.quit()

display_queue = None

def display_text(text: str) -> bool:
    global display_queue
    display_queue.put(('display_text', text))

def display_image(img_fn: str) -> bool:
    global display_queue
    display_queue.put(('display_image', img_fn))

def init_display():
    global display_queue
    engine = DisplayEngine()
    display_queue = engine.display_queue
    engine.start()
