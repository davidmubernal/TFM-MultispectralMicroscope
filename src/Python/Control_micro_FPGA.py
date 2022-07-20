import tkinter
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter.ttk import Progressbar

import serial
import serial.tools.list_ports
import time
import os
from cv2 import cv2
import numpy as np
import os
import shutil
import datetime
import threading
from PIL import Image, ImageTk


from PIL import Image
import struct

class control_FPGA():

    def __init__(self, ser):
        self.version = "V7.6"
        print(f"> Interfaz Sistema de Autoenfoque OpenFlexure {self.version} ")
        self.ser = ser

        # Fecha y hora para los archivos
        self.timestamp = '{:%m%d-%H%M}'.format(datetime.datetime.now())

        # Comprueba si se ha seleccionado el path
        self.flag_carpeta = False

        # variable auxiliar contador de número de imagenes desde que inicio la interfaz
        self.aux = 0
        self.aux_af = 0
        self.count_m1 = 0
        self.count_m2 = 0
        self.count_m3 = 0

        #inicialización de variables
        self.directorio = ""
        self.flag_carpeta = False
        self.dirflag = False
        self.homeflag = False
        self.M1_is_on = True
        self.M2_is_on = True
        self.M3_is_on = True
        self.M_is_on = True
        self.DIR_is_on = True
        self.sobel_is_on = False
        self.btnHOME_is_on = True
        self.cap_is_on = False
        self.on = "ON"
        self.off = "OFF"
        self.img_enf_maximo=False


        self.pil_img_red = None
        self.pil_img_green = None
        self.pil_img_blue = None
        self.pil_img_violet = None

    # -----------------
    # --- FUNCIONES ---
    # -----------------
    # Función para determinar la carpeta de trabajo donde guardar las imagenes
    def carpeta_imagenes(self):
        self.flag_carpeta = True
        directorio = filedialog.askdirectory()
        print(f'> Ruta establecida para guardar las imágenes: {directorio}')

        self.dir_simples = directorio + '/IMG_Simples'
        os.makedirs(self.dir_simples, exist_ok=True)

        self.dir_autoenfoque = directorio + '/IMG_Autoenfoque'
        os.makedirs(self.dir_autoenfoque, exist_ok=True)

        self.dir_spectral = directorio + '/IMG_Spectral'
        os.makedirs(self.dir_spectral, exist_ok=True)

        self.directorio_trabajo.delete(0, tkinter.END)
        self.directorio_trabajo.insert(0, directorio)
        self.pos.config(text="Estado: Directorio seleccionado")

    # Función para reiniciar la interfaz
    def reset(self):
        print("> Interfaz reseteada")
        self.root.destroy()
        interfaz = control_FPGA()
        interfaz.createGUI()


    # Mueve las imágenes al directorio correspondiente
    def ordena_img(self, nombrebin, nombre, direccion):
        # shutil.copy(nombrebin + '.bin', direccion)
        shutil.copy(nombre + '.png', direccion)

        # os.remove(nombrebin + '.bin')
        os.remove(nombre + '.png')


    # Funcion para enviar las instrucciones a la FPGA por el puerto serie
    def env_serial(self, arg):
        bin_num = arg.to_bytes(8, byteorder='big')
        self.ser.write(bin_num)
        if arg == 0 or arg == 255:
            pass
        else:
            print("- Instruccion " + str(arg) + " enviada")
            print("----")


    # Generación del archivo PGM:
    def bin_to_png(self, ancho, alto, nombre_bin, nombre_png, imagen_interfaz=None):
        if imagen_interfaz == None:
            imagen_interfaz = self.imagen_interfaz
        # - Se crea una array de numpy con los bytes del archivo .bin
        archivo_bin = nombre_bin + ".bin"
        arr = np.fromfile(archivo_bin, dtype=np.uint8, count=-1, sep='', offset=0)

        data_png = struct.pack('B' * len(arr), *[pixel for pixel in arr])
        size = ancho, alto
        archivo_png = Image.frombuffer('L', size, data_png)
        archivo_png.save(nombre_png + '.png')
        os.remove(archivo_bin)
        imagen_interfaz = archivo_png

        suma = np.sum(arr)
        return (suma)

    def hyperspectral_img_capture(self):
        """
        Realiza la captura de una imagen y mueve el conjunto de filtros
        """
         # Aniadir a la lista tantos filtros como tenga el sistema
        self.filters = {"red":{ "binary":64, "image":self.img_red, "panel":self.panel_red,"pil_img":self.pil_img_red},
                   "green":{"binary":65, "image":self.img_green, "panel":self.panel_green, "pil_img":self.pil_img_green},
                   "blue":{"binary":66, "image":self.img_blue, "panel":self.panel_blue, "pil_img":self.pil_img_blue},
                   "ultraviolet":{"binary":67, "image":self.img_violet, "panel":self.panel_violet, "pil_img":self.pil_img_violet}
        }
        for _filter in self.filters.keys():
            self.root.update()
            
            print("> Mover a filtro {}".format(_filter))
            print("----------------------------------")
            # if not _filter[1] == 64:
            self.env_serial(self.filters[_filter]["binary"])

            time.sleep(5) # El motor no bloquea la FPGA, necesita 
            self.env_serial(4)
            nombrebin = "IMG_BIN_" + str(self.aux) + '_' + _filter + '_' + self.timestamp

            self.pos.config(text="Estado: Guardando imagen..." )
            nombre = "IMG_" + str(self.aux) + '_' + _filter + '_' + self.timestamp
            self.aux = self.aux + 1

            print("> Guardando imagen...")

            self.progress_bar.grid(row=6, column=3, columnspan=4, padx=5, pady=5)

            self.lee_serial(nombrebin, 320, 240)

            self.progress_bar.grid(row=6, column=3, columnspan=4, padx=5, pady=5)
            self.progress_bar.grid_forget()

            self.bin_to_png(320, 240, nombrebin, nombre, imagen_interfaz=self.filters[_filter]["image"])

            print("> Imagen .PNG recibida")
            print("----------------------------------") 

            x = threading.Thread(target= self.ordena_img, args=(nombrebin, nombre, self.dir_spectral))
            x.start()

            time.sleep(1)
            self.filters[_filter]["pil_img"] = Image.open(f'{self.dir_spectral}/{nombre}.png')
            resized_img = self.filters[_filter]["pil_img"].resize((self.width_hyperImages,self.height_hyperImages))
            self.filters[_filter]["image"]= ImageTk.PhotoImage(resized_img)
            self.filters[_filter]["panel"].configure(image=self.filters[_filter]["image"])


        self.pos.config(text="Estado: Imagen recibida " )
        self.root.update()
        time.sleep(0.5)

        self.pos.config(text="Estado inicial: Esperando instrucciones... " )
        self.root.update()

    # Función que capturar la imagen
    def captura_img_serie(self):
        if self.cap_is_on:
            self.cap.config(text="Activar cam")
            self.cap_is_on = False
            print("- Imagen capturada")
            self.env_serial(2)
            self.pos.config(text="Estado Inicial: Esperando instrucciones... ")
        else:
            self.cap.config(text="Capturar IMG")
            self.cap_is_on = True
            print("- Captura deshabilitada")
            self.env_serial(1)
            self.pos.config(text="Estado: Imagen capturada ")


    #Activa/Desactiva el filtro sobel
    def sobel(self):
        if self.sobel_is_on:
            self.sobel_is_on = False
            print("- Filtro Sobel-H OFF")
            self.env_serial(192)
            self.env_serial(0)
        else:
            self.sobel_is_on = True
            print("- Filtro Sobel-H ON")
            self.env_serial(192)
            self.env_serial(0)


#---
    # Función que manda la instrucción para iniciar el sist. de AutoEnfoque
    def autoenfoque(self):
        # TODO: Comprobar que está pasando aquí, algo no funciona como debería
        if self.homeflag == True:
            self.env_serial(5)
            self.env_serial(0)
            self.env_serial(133)
            self.env_serial(0)
            self.img = PhotoImage(file=r"./img/img_micro22.png")
            self.panel = Label(self.root, image=self.img)
            self.panel.grid(row=3, column=3, columnspan=4, rowspan=7, padx=5, pady=5)

            self.save_img_autofocus()  # como no detecto cuando la FGPA termina el mov del motor y manda la siguiente foto lo hago por "software"
            self.img_enf_maximo=True

            self.pos.config(text="Estado: Ajustando a la mejor posición" )

            self.save_img_serie()

            self.img_enf_maximo=False
            self.pos.config(text="Estado: IMANGEN ENFOCADA GUARDADA " )
            print("-- IMANGEN ENFOCADA GUARDADA -- ")
            time.sleep(0.5)
            self.pos.config(text="Estado: Esperando instrucciones... " )

        else:
            self.pos.config(text="Estado: Primero seleccione un directorio! ")


    # Guarda las imagenes en la estructura de directorios creada
    def save_img_serie(self):
        if self.flag_carpeta == True:

            self.root.update()
            self.env_serial(4)

            nombrebin = "IMG_BIN_" + str(self.aux) + '_' + self.timestamp

            if self.img_enf_maximo==False:
                self.pos.config(text="Estado: Guardando imagen..." )
                nombre = "IMG_" + str(self.aux) + '_' + self.timestamp
                self.aux = self.aux + 1
            else:
                self.pos.config(text="Estado: Guardando imagen enfocada..." )
                nombre = "IMG_ENFOCADA" + str(self.aux_af) + '_' + self.timestamp
                self.aux_af = self.aux_af + 1

            print("> Guardando imagen...")

            self.progress_bar.grid(row=6, column=3, columnspan=4, padx=5, pady=5)

            self.lee_serial(nombrebin, 320, 240)

            self.progress_bar.grid(row=6, column=3, columnspan=4, padx=5, pady=5)
            self.progress_bar.grid_forget()

            self.bin_to_png(320, 240, nombrebin, nombre)

            img_interfaz = ImageTk.PhotoImage(self.imagen_interfaz)
            self.panel.configure(image=img_interfaz)
            self.panel.image = img_interfaz

            print("> Imagen .PNG recibida")
            print("----------------------------------")
            
            x = threading.Thread(target= self.ordena_img, args=(nombrebin, nombre, self.dir_simples))
            x.start()

            self.pos.config(text="Estado: Imagen recibida " )
            self.root.update()
            time.sleep(0.5)

            self.pos.config(text="Estado inicial: Esperando instrucciones... " )
            self.root.update()

        else:
            self.pos.config(text="Estado: Primero seleccione un directorio! ")
            print("! Seleccione un directorio para guardar las imágenes")


    # Lectura del puerto serie, para recibir la imagen
    def lee_serial(self, nombre_bin, ancho, alto):

        self.dimensiones = ancho * alto
        archivo_bin = nombre_bin + ".bin"
        fout = open(archivo_bin, 'wb')
        self.total_bits = 0

        while self.total_bits < self.dimensiones:
            bytesToRead = self.ser.inWaiting()
            data = self.ser.read(bytesToRead)
            fout.write(data)
            self.total_bits = len(data) + self.total_bits

            if self.total_bits < (self.dimensiones * 1 / 5):
                self.barra_progreso(0)
                self.root.update_idletasks()
            elif (self.dimensiones * 1 / 5) < self.total_bits < (self.dimensiones * 2 / 5):
                self.barra_progreso(20)
                self.root.update_idletasks()
            elif (self.dimensiones * 2 / 5) < self.total_bits < (self.dimensiones * 3 / 5):
                self.barra_progreso(40)
                self.root.update_idletasks()
            elif (self.dimensiones * 3 / 5) < self.total_bits < (self.dimensiones * 4 / 5):
                self.barra_progreso(60)
                self.root.update_idletasks()
            elif (self.dimensiones * 4 / 5) < self.total_bits < (self.dimensiones):
                self.barra_progreso(80)
                self.root.update_idletasks()
            elif self.total_bits == (self.dimensiones):
                self.barra_progreso(100)
                self.root.update_idletasks()
                time.sleep(0.1)

        print("- total bits recibidos:" + str(self.total_bits))


    # Función para guardar las imaágenes obtenidas en el modo AutoEnfoque
    def save_img_autofocus(self):
        if self.flag_carpeta == True:

            self.env_serial(4)

            lista_datos_enfoque = []
            max_ele = 0

            for i in range(0, 3):
                nombrebin = "IMG_BIN_AF" + str(i) + '_' + self.timestamp
                nombre = "IMG_AF" + str(i) + '_' + self.timestamp

                self.pos.config(text="Estado: proceso de autoenfoque... %s/3" % i )

                #--
                self.lee_serial(nombrebin, 320, 240)
                #--

                a = self.bin_to_png(320, 240, nombrebin, nombre)
                time.sleep(0.5)

                print("- Archivo procesado, PNG listo")
                print(str(i) + ")------------------------")
                print("Suma DEC:" + str(a))
                print("Suma HEX:" + str(hex(a)))
                lista_datos_enfoque.append(a)
                print("----------------------------------")

                # mueve imgs
                x = threading.Thread(target=self.ordena_img(nombrebin, nombre, self.dir_autoenfoque))
                x.start()


            for j in range(1, len(lista_datos_enfoque)):
                if int(lista_datos_enfoque[i]) > max_ele:
                    max_ele = int(lista_datos_enfoque[i])

            print("Lista de datos obtenidos:")
            print(lista_datos_enfoque)
            print(
                "- Posición máximo: " + str(
                    lista_datos_enfoque.index(max(lista_datos_enfoque))) + " -  Valor: " + str(
                    max(lista_datos_enfoque)))
            print("----------------------------------")
            time.sleep(0.2)
        else:
            self.pos.config(text="Estado: Primero seleccione un directorio! ")
            print("! Seleccione un directorio para guardar las imágenes")


    # -------- Control de los Motores ----------

    def btnHOME(self):
        if self.btnHOME_is_on:
            self.pos.config(text="Estado: Colocando en posición de referencia...")
            self.btnHOME_is_on = False
            print("btn HOME on")

            if self.flag_carpeta == True:
                self.env_serial(3)
                self.info.configure(text=f"Posición muestra: {self.count_m1}-{self.count_m2}-{self.count_m3}")

            else:
                self.pos.config(text="Estado: Primero seleccione un directorio")

            self.homeflag = True
            self.M1.config(text= "Ajustar")
            self.M2.config(text= "Ajustar")
            self.M3.config(text= "Ajustar")
            self.M.config(text= "Ajustar")
            self.dir.config(text="ARRIBA")
            self.DIR_is_on = True
        else:
            self.pos.config(text="Estado Inicial: Esperando instrucciones... ")
            self.btnHOME_is_on = True
            print("btn HOME off")
            self.env_serial(0)
            self.homeflag = False
            self.count_m1 = 0
            self.count_m2 = 0
            self.count_m3 = 0


    def switchDIR(self):
        if self.DIR_is_on:
            self.dir.config(text="ABAJO")  # elimnino dir_on
            self.DIR_is_on = False
            print("Movimiento descendente")
            self.env_serial(128)
            self.env_serial(0)
            self.dirflag = False
        else:
            self.dir.config(text="ARRIBA")
            self.DIR_is_on = True
            print("Movimiento ascendente")
            self.env_serial(128)
            self.env_serial(0)
            self.dirflag = True


    def switchM1(self):
        if self.homeflag == False:
            if self.M1_is_on:
                self.M1.config(text=self.on)
                self.M1_is_on = False
                print("Motor1 on")
                self.env_serial(129)
                self.env_serial(0)
            else:
                self.M1.config(text=self.off)
                self.M1_is_on = True
                print("Motor1 off")
                self.env_serial(129)
                self.env_serial(0)
        else:
            self.M1.config(text= "Ajustar")
            self.M1_is_on = False
            print("Motor1 pulsado")
            self.env_serial(129)
            self.env_serial(0)
            if self.dirflag == True:
                self.count_m1 = self.count_m1 + 1
            elif self.dirflag == False:
                if self.count_m1 == 0:
                    self.count_m1 = self.count_m1
                else:
                    self.count_m1 = self.count_m1 - 1
            self.pos.config(text="Estado: Ajuste pre-autoenfoque")
            self.info.configure(text=f"Posición muestra: {self.count_m1}-{self.count_m2}-{self.count_m3}")
            self.root.update()


    def switchM2(self):
        if self.homeflag == False:
            if self.M2_is_on:
                self.M2.config(text= self.on)
                self.M2_is_on = False
                print("Motor2 on")
                self.env_serial(130)
                self.env_serial(0)  # 255
            else:
                self.M2.config(text= self.off)
                self.M2_is_on = True
                print("Motor2 off")
                self.env_serial(130)
                self.env_serial(0)
        else:
            self.M2.config(text= "Ajustar")
            self.M2_is_on = False
            print("Motor2 pulsado")
            self.env_serial(130)
            self.env_serial(0)
            if self.dirflag == True:
                self.count_m2 = self.count_m2 + 1
            elif self.dirflag == False:
                if self.count_m2 == 0:
                    self.count_m2 = self.count_m2
                else:
                    self.count_m2 = self.count_m2 - 1
            self.pos.config(text="Estado: Ajuste pre-autoenfoque")
            self.info.configure(text=f"Posición muestra: {self.count_m1}-{self.count_m2}-{self.count_m3}")
            self.root.update()


    def switchM3(self):
        if self.homeflag == False:
            if self.M3_is_on:
                self.M3.config(text=self.on)
                self.M3_is_on = False
                print("Motor3 on")
                self.env_serial(131)
                self.env_serial(0)
            else:
                self.M3.config(text=self.off)
                self.M3_is_on = True
                print("Motor3 off")
                self.env_serial(131)
                self.env_serial(0)
        else:
            self.M3.config(text= "Ajustar")
            self.M3_is_on = False
            print("Motor2 pulsado")
            self.env_serial(131)
            self.env_serial(0)
            if self.dirflag == True:
                self.count_m3 = self.count_m3 + 1
            elif self.dirflag == False:
                if self.count_m3 == 0:
                    self.count_m3 = self.count_m3
                else:
                    self.count_m3 = self.count_m3 - 1
            self.pos.config(text="Estado: Ajuste pre-autoenfoque")
            self.info.configure(text=f"Posición muestra: {self.count_m1}-{self.count_m2}-{self.count_m3}")
            self.root.update()


    def switchM(self):
        if self.homeflag == False:
            if self.M_is_on:
                self.M.config(text=self.on)
                self.M1.config(text=self.on)
                self.M2.config(text=self.on)
                self.M3.config(text=self.on)
                self.M_is_on = False
                self.M1_is_on = False
                self.M2_is_on = False
                self.M3_is_on = False
                print("All Motor on")
                self.env_serial(132)
                self.env_serial(0)
            else:
                self.M.config(text=self.off)
                self.M1.config(text=self.off)
                self.M2.config(text=self.off)
                self.M3.config(text=self.off)
                self.M_is_on = True
                self.M1_is_on = True
                self.M2_is_on = True
                self.M3_is_on = True
                print("All Motor off")
                self.env_serial(132)
                self.env_serial(0)
        else:
            self.M.config(text= "Ajustar")
            self.M1.config(text= "Ajustar")
            self.M2.config(text= "Ajustar")
            self.M3.config(text= "Ajustar")
            self.M_is_on = False
            self.M1_is_on = False
            self.M2_is_on = False
            self.M3_is_on = False
            print("All Motor on")
            self.env_serial(132)
            self.env_serial(0)
            if self.dirflag == True:
                self.count_m1 = self.count_m1 + 1
                self.count_m2 = self.count_m2 + 1
                self.count_m3 = self.count_m3 + 1
            elif self.dirflag == False:
                if self.count_m1 == 0:
                    self.count_m1 = self.count_m1
                else:
                    self.count_m1 = self.count_m1 - 1
                if self.count_m2 == 0:
                    self.count_m2 = self.count_m2
                else:
                    self.count_m2 = self.count_m2 - 1
                if self.count_m3 == 0:
                    self.count_m3 = self.count_m3
                else:
                    self.count_m3 = self.count_m3 - 1
            self.pos.config(text="Estado: Ajuste pre-autoenfoque")
            self.info.configure(text=f"Posición muestra: {self.count_m1}-{self.count_m2}-{self.count_m3}")
            self.root.update()


    # ---------------------------INTERFAZ----------------------------------------------
    def createGUI(self):
        self.root = Tk()
        self.root.resizable(width=False, height=False)
        self.color_fondo = "#FFFFFF"
        self.root['background'] = self.color_fondo

        # ---MENU ---
        menubar = Menu(self.root)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Instrucciones", command=self.instrucciones)
        filemenu.add_command(label="Esquema FPGA", command=self.esquema)
        filemenu.add_command(label="About", command=self.about)
        filemenu.add_command(label="Reset", command=self.reset)
        filemenu.add_command(label="Exit", command=self.root.quit)

        configmenu = Menu(menubar, tearoff=0)
        configmenu.add_command(label="Filtro Sobel-H", command=self.sobel)
        configmenu.add_command(label="Exit", command=self.root.quit)

        # filemenu.add_separator()

        menubar.add_cascade(label="Menu", menu=filemenu)
        menubar.add_cascade(label="Configuración", menu=configmenu)

        # ---TABS ---
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both",expand="no")
        self.simple_image = ttk.Frame(self.tabs)
        self.spectral_image = ttk.Frame(self.tabs)
        self.tabs.add(self.simple_image, text="Simple Mode",padding=20)
        self.tabs.add(self.spectral_image, text="Spectral Mode",padding=20)
        
        # ---TABS 1 - Simple Image---

        # titulo de ventana - icono
        self.root.title('- FPGA - Interfaz de control del microscopio')
        self.root.iconbitmap('./img/logo.ico')

        # Define el directorio de trabajo:
        selectdir = Button(self.simple_image, text="Path", font=("Helvetica", 8), command=lambda: self.carpeta_imagenes())
        selectdir.grid(row=0, column=1, sticky=E, padx=5, pady=10)
        self.carpeta_trabajo = Entry(self.simple_image, width=50, text="Seleccionar carpeta", font=("Calibri Light", 10))
        self.carpeta_trabajo.grid(row=0, column=2, columnspan=3, sticky=W, padx=5, pady=10)
        self.carpeta_trabajo.insert(0, "Seleccione un directorio para guardar las imágenes")
        self.directorio_trabajo = self.carpeta_trabajo

        # Etiqueta que define la posición de la muestra
        self.pos = Label(self.simple_image, text="Estado inicial: Esperando instrucciones... ", font=('Calibri Light', 11), bg=self.color_fondo)
        self.pos.grid(row=1, column=1, sticky=W+E, padx=10, pady=10, columnspan=15)

        # Etiqueta que define el estado en el que se encuentra trabajando el microscopio
        self.info = Label(self.simple_image, text="Posición muestra: %-%-%", font=('Calibri Light', 9), bg=self.color_fondo)
        self.info.grid(row=3, column=1, sticky=W+E, padx=10, pady=0, columnspan=2)

        # Botón que inicia el movimiento del microscopio, desplazandose al punto de referencia
        self.btn_home = Button(self.simple_image, text="HOME", font=("Helvetica", 9), bg=None, command=lambda: self.btnHOME())
        self.btn_home.grid(row=2, column=2, sticky=E, pady=10)

        # Botón que inicia el proceso de AUTOENFOQUE
        self.btn_focus = Button(self.simple_image, text="AUTOENFOQUE", font=("Helvetica", 9), bg=None, command=lambda: self.autoenfoque())
        self.btn_focus.grid(row=2, column=3, pady=10)

        # Botón que activa el filtro SOBEL
        self.btn_sobel = Button(self.simple_image, text="SOBEL", font=("Helvetica", 9), bg=None, command=lambda: self.sobel())
        self.btn_sobel.grid(row=2, column=4, sticky=W, pady=10)

        # Botones de control de los motores:
        self.M1 = Label(self.simple_image, text="Estado", font=("Calibri Light", 10), bg=self.color_fondo)
        self.M1.grid(row=4, column=2, sticky=W, pady=2)
        self.btnM1 = Button(self.simple_image, text="Motor M1", font=("Calibri Light", 10), command=lambda: self.switchM1())
        self.btnM1.grid(row=4, column=1, sticky=E, pady=2)

        self.M2 = Label(self.simple_image, text="Estado", font=("Calibri Light", 10), bg=self.color_fondo)
        self.M2.grid(row=5, column=2, sticky=W, pady=2)
        self.btnM2 = Button(self.simple_image, text="Motor M2", font=("Calibri Light", 10), command=lambda: self.switchM2())
        self.btnM2.grid(row=5, column=1, sticky=E, pady=2)

        self.M3 = Label(self.simple_image, text="Estado", font=("Calibri Light", 10), bg=self.color_fondo)
        self.M3.grid(row=6, column=2, sticky=W, pady=2)
        self.btnM3 = Button(self.simple_image, text="Motor M3", font=("Calibri Light", 10), command=lambda: self.switchM3())
        self.btnM3.grid(row=6, column=1, sticky=E, pady=2)

        self.M = Label(self.simple_image, text="Estado", font=("Calibri Light", 10), bg=self.color_fondo)
        self.M.grid(row=7, column=2, sticky=W, pady=4)
        self.btnM = Button(self.simple_image, text="Todos", font=("Calibri Light", 10), command=lambda: self.switchM())
        self.btnM.grid(row=7, column=1, sticky=E, pady=2)

        # Botón que define la dirección de los motores
        self.dir = Label(self.simple_image, text="Estado", font=("Calibri Light", 10), bg=self.color_fondo)
        self.dir.grid(row=9, column=2, sticky=W, pady=5)
        self.btnDIR = Button(self.simple_image, text="Dirección", font=("Calibri Light", 10), command=lambda: self.switchDIR())
        self.btnDIR.grid(row=9, column=1, sticky=E, pady=2)

        # Botón que captura la imagen
        self.cap = Button(self.simple_image, text="Capturar IMG", bg=None, command=lambda: self.captura_img_serie())
        self.cap.grid(row=10, column=3, sticky=E, padx=5, pady=5)

        # Botón para obtener la imagen de la FPGA
        self.recibir_img = Button(self.simple_image, text="Guardar IMG", bg=None, command=lambda: self.save_img_serie())
        self.recibir_img.grid(row=10, column=4, sticky=W, padx=5, pady=5)


        #Versión del código ejecutado
        self.version = Label(self.simple_image, text= self.version)
        self.version.grid(row=12, column=1, sticky=W, pady=2)

        # Define la imagen obtenida de la FPGA
        self.img = PhotoImage(file=r"./img/img_micro22.png")
        self.panel = Label(self.simple_image, image=self.img)
        self.panel.grid(row=3, column=3, columnspan=4, rowspan=7, padx=5, pady=5)

        # Barra de progreso
        self.progress_bar = Progressbar(self.simple_image, orient=HORIZONTAL, length=160, mode='determinate')
        self.progress_bar.grid(row=6, column=3, columnspan=4, padx=5, pady=5)
        self.progress_bar.grid_forget()

        # ---TABS 2 - Spectral Image---

        # Define el directorio de trabajo:
        selectdir = Button(self.spectral_image, text="Path", font=("Helvetica", 8), command=lambda: self.carpeta_imagenes())
        selectdir.grid(row=0, column=1, sticky=E, padx=5, pady=10)
        self.carpeta_trabajo = Entry(self.simple_image, width=50, text="Seleccionar carpeta", font=("Calibri Light", 10))
        self.carpeta_trabajo.grid(row=0, column=2, columnspan=3, sticky=W, padx=5, pady=10)
        self.carpeta_trabajo.insert(0, "Seleccione un directorio para guardar las imágenes")
        self.directorio_trabajo = self.carpeta_trabajo

        # Botón para obtener la imagen de la FPGA
        self.recibir_img_spectral = Button(self.spectral_image, text="Spectral IMG", bg=None, command=lambda: self.hyperspectral_img_capture())
        self.recibir_img_spectral.grid(row=1, column=1, sticky=W, padx=5, pady=5)

        self.carpeta_trabajo_spectral = Entry(self.spectral_image, width=50, text="Seleccionar carpeta", font=("Calibri Light", 10))
        self.carpeta_trabajo_spectral.grid(row=0, column=2, columnspan=5, sticky=W, padx=5, pady=10)
        self.carpeta_trabajo_spectral.insert(0, "Seleccione un directorio para guardar las imágenes")
        self.directorio_trabajo = self.carpeta_trabajo_spectral

        # CheckBox Red spectrum
        self.red_status = IntVar()
        self.checkBox_red = Checkbutton(self.spectral_image, var=self.red_status, text="Red", command=lambda: self.change_spectral_image())
        self.checkBox_red.grid(row=2, column=1, sticky=W, padx=5, pady=5)
        
        # CheckBox Green spectrum
        self.green_status = IntVar()
        self.checkBox_green = Checkbutton(self.spectral_image, var=self.green_status, text="Green", command=lambda: self.change_spectral_image())
        self.checkBox_green.grid(row=3, column=1, sticky=W, padx=5, pady=5)

        # CheckBox Blue spectrum
        self.blue_status = IntVar()
        self.checkBox_blue = Checkbutton(self.spectral_image, var=self.blue_status, text="Blue", command=lambda: self.change_spectral_image())
        self.checkBox_blue.grid(row=4, column=1, sticky=W, padx=5, pady=5)

        # Slider red spectrum
        self.slider_red = Scale(self.spectral_image, from_ = 0, to = 100,  orient = HORIZONTAL, command=self.change_spectral_image)
        self.slider_red.grid(row=2, column=2, sticky=W, padx=5, pady=5)

        # Slider green spectrum
        self.slider_green = Scale(self.spectral_image, from_ = 0, to = 100,  orient = HORIZONTAL, command=self.change_spectral_image)
        self.slider_green.grid(row=3, column=2, sticky=W, padx=5, pady=5)
        
        # Slider blue spectrum
        self.slider_blue = Scale(self.spectral_image, from_ = 0, to = 100,  orient = HORIZONTAL, command=self.change_spectral_image)
        self.slider_blue.grid(row=4, column=2, sticky=W, padx=5, pady=5)

        # Define la imagen suma
        self.img_spectral = PhotoImage(file=r"./img/img_micro22.png")
        self.panel_spectral = Label(self.spectral_image, image=self.img_spectral)
        self.panel_spectral.grid(row=2, column=3, columnspan=4, rowspan=3, padx=5, pady=5)

        self.height_hyperImages = 90
        self.width_hyperImages = 120
        #Image visualization red
        self.img_red = PhotoImage(file=r"./img/img_micro22.png", height=self.height_hyperImages, width=self.width_hyperImages)
        self.panel_red = Label(self.spectral_image, image=self.img_red)
        self.panel_red.grid(row=5, column=2, columnspan=1, rowspan=1, padx=0, pady=0)

        #Image visualization green
        self.img_green = PhotoImage(file=r"./img/img_micro22.png", height=self.height_hyperImages, width=self.width_hyperImages)
        self.panel_green = Label(self.spectral_image, image=self.img_green)
        self.panel_green.grid(row=5, column=3, columnspan=1, rowspan=1, padx=0, pady=0)

        #Image visualization blue
        self.img_blue = PhotoImage(file=r"./img/img_micro22.png", height=self.height_hyperImages, width=self.width_hyperImages)
        self.panel_blue = Label(self.spectral_image, image=self.img_blue)
        self.panel_blue.grid(row=5, column=4, columnspan=1, rowspan=1, padx=0, pady=0)

        #Image visualization violeta
        self.img_violet = PhotoImage(file=r"./img/img_micro22.png", height=self.height_hyperImages, width=self.width_hyperImages)
        self.panel_violet = Label(self.spectral_image, image=self.img_violet)
        self.panel_violet.grid(row=5, column=5, columnspan=1, rowspan=1, padx=0, pady=0)

        # ---Configuracion ---
        self.root.config(menu=menubar)
        self.root.mainloop()

    def change_spectral_image(self, value=None):
        if self.red_status.get():
            red_value = self.slider_red.get()/100
        else:
            red_value = 0
        if self.green_status.get():
            green_value = self.slider_green.get()/100
        else:
            green_value = 0
        if self.blue_status.get():
            blue_value = self.slider_blue.get()/100
        else:
            blue_value = 0
        
        self.pil_spectral = np.array(self.filters["red"]["pil_img"]) * red_value + np.array(self.filters["green"]["pil_img"]) * green_value + np.array(self.filters["blue"]["pil_img"]) * blue_value
        self.pil_spectral = Image.fromarray(self.pil_spectral)
        # self.pil_spectral.save("./temp.png")
        self.img_spectral = ImageTk.PhotoImage(self.pil_spectral)
        self.panel_spectral.configure(image=self.img_spectral)
    # ---------------------------INFORMACIÓN-------------------------------------------
    def barra_progreso(self, valor):
        self.progress_bar['value'] = int(valor)
        self.root.update_idletasks()

    def about(self):
        toplevel = tkinter.Toplevel(self.root)
        label0 = tkinter.Label(toplevel, text="\n Interfaz de control FPGA", font=("Helvetica", 9, "bold"))
        label0.grid(row=0, column=1, padx=1, sticky="s")

        label1 = ttk.Label(toplevel, text="\n    Esta trabajo forma parte del TFM : "
                                          "\n                                                                                  "
                                          "\n     SISTEMA DE AUTOENFOQUE MEDIANTE FPGA PARA MICROSCOPIO DE BAJO                "
                                          "\n     COSTE Y HARDWARE LIBRE CON POSICIONAMIENTO DE BISAGRAS FLEXIBLES             "
                                          "\n                                                                                  "
                                          "\n    La interfaz permite el control del sistema de posicionamiento, la obtención   "
                                          "\n    de imágenes y un proceso de enfoque automático desarrollado en FPGA.          "
                                          "\n                                                                                  "
                                          "\n    Toda la información del proyecto se encuentra disponible en:                  "
                                          "\n            https://github.com/URJCMakerGroup/Autofocus_Delta_Stage               "
                                          "\n    ")

        label1.grid(row=1, column=1, padx=1, sticky="s")
        close_btn = ttk.Button(toplevel, text="     ok     ", command=toplevel.destroy)
        close_btn.grid(row=2, column=1)
        label2 = ttk.Label(toplevel, text=" ")
        label2.grid(row=3, column=1, padx=1, sticky="s")

    def esquema(self):
        x = threading.Thread(target=self.info_esquema, args=())
        x.start()

    def info_esquema(self):
        img = cv2.imread(r"./img/esquema.png", cv2.IMREAD_COLOR)
        cv2.imshow("Esquema control FPGA", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def instrucciones(self):
        toplevel = tkinter.Toplevel(self.root)
        label0 = tkinter.Label(toplevel, text="\n Instrucciones de uso:", font=("Helvetica", 9, "bold"))
        label0.grid(row=0, column=1, padx=1, sticky="s")

        label1 = ttk.Label(toplevel, text="\n    La interfaz permite el control de los motores para el ajuste de la muestra. "
                                          "\n                                                                          "
                                          "\n    En primer lugar es preciso definir un directorio de trabajo pulsando el"
                                          "\n    botón path. A partir de ahí se puede controlar los diferentes motores y"
                                          "\n    su dirección, capturar imágenes o guardarlas en PNG el path seleccionado."
                                          "\n                                                                          "
                                          "\n    - El botón HOME, fija el sistema de posicionamiento en el lugar de referencia"
                                          "\n      Una vez en la posición de referencia se puede realizar el autoenfoque."
                                          "\n                                                                          "
                                          "\n    - El botón SOBEL, aplica ese filtro a la imagen (de forma horizontal)        "
                                          "\n                                                                          "
                                          "\n    - El botón AUTOENFOQUE, inicia el proceso para obtener la imagen mejor enfocada "
                                          "\n    ")

        label1.grid(row=1, column=1, padx=1, sticky="s")

        close_btn = ttk.Button(toplevel, text="     ok     ", command=toplevel.destroy)
        close_btn.grid(row=2, column=1)

        label2 = ttk.Label(toplevel, text=" ")
        label2.grid(row=3, column=1, padx=1, sticky="s")


# -------------------------------------------------------------------------
if __name__ == "__main__":
    # app = control_FPGA(serial.Serial())
    # app.createGUI()
    ports = [comport.device for comport in serial.tools.list_ports.comports()]
    text = [str(i)+":"+port for i,port in enumerate(ports)]
    select = input("Select the port with the FPGA:{}".format(text))

    with serial.Serial() as ser:
        ser.port=ports[int(select)]#'COM4'
        ser.baudrate=115200
        ser.timeout=0
        ser.parity=serial.PARITY_NONE
        ser.stopbits=serial.STOPBITS_TWO
        ser.bytesize=serial.EIGHTBITS
        try:
            ser.open()
        except:
            pass
        if ser.is_open:
                print("-- FPGA conectada --")
                app = control_FPGA(ser)
                app.createGUI()
        else:
            print("-- Error no serial comunication active --")