'''
#pip install opencv-python-headless
#pip install twilio
#pip install opencv-contrib-python
pip install pyserial
Para intalar librerias faltantes,
abrir consola e introducir lo siguiente:
'pip install nombre_de_la_libreria'
'''

import cv2
import numpy as np
import time
from twilio.rest import Client
import datetime as dt
##import pyserial





class IluminacionDetectada:
    
    def __init__(self):
##        video_source = 'mont.jpg' #image_source.jpg'
##        video_source = 'Montaña.mp4'
        video_source = 0 # Cambia el índice si tienes varias cámaras (índice webcam: 1)
##        video_source = 'nombre_del_video.mp4' # Archivo .mp4 local (saber si hay en un incendio o no)
        # Inicializamos la captura de video desde la cámara
        self.cap = cv2.VideoCapture(video_source)
        
        
        # Inicializamos el valor del promedio de área anterior
        self.promedio_anterior = 0
        self.pausa = False
        
##        CREARSE UNA CUENTA EN TWILIO
##        self.client = Client("your_account_sid", "your_auth_token")
        self.client = Client("", "")
        
        # Verificar si la captura de video se abrió correctamente
        if not self.cap.isOpened():
            print("No se pudo abrir el video.")
            self.cambiar_video_source()  # Llama a la función para cambiar el dispositivo de entrada de video
            self.cap = cv2.VideoCapture(self.video_source)  # Reinicializa la captura con el nuevo video_source

    def enviar_alerta(self, mensaje):
        message = self.client.messages.create(
            to = +11234567890, # Número de destino (número propio)
            from_ = +11234567890, # Número en Twilio
            body = mensaje,
        )
        print(f"Alerta enviada: {message.sid} {mensaje}")

    def detectar_iluminacion(self, frame):
        frame = cv2.resize(frame, (800, 600))
        frame1 = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.medianBlur(frame1, 5)
        _,frame3 = cv2.threshold(frame2,127,255,cv2.THRESH_BINARY)

##        # Valor del umbralizado es el promedio del área del vecindario 
        atmc = cv2.adaptiveThreshold(frame3,255,cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,11,2)
##        # Valor del umbralizado es una suma ponderada (correlación cruzada con una ventana Gaussiana)
        atgc = cv2.adaptiveThreshold(frame3,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)

 
        # Definimos los rangos de colores para detectar luz naranja, amarilla y azul
        hsv_frame = cv2.medianBlur(frame, 5)
        hsv_frame = cv2.cvtColor(hsv_frame, cv2.COLOR_BGR2HSV)

        # Definimos los rangos de color para cada componente del fuego
        bajo_rojo1 = np.array([0, 70, 50])
        alto_rojo1 = np.array([12, 255, 255])
        bajo_rojo2 = np.array([160, 70, 50])
        alto_rojo2 = np.array([190, 255, 255])
        bajo_naranja = np.array([10, 70, 50])
        alto_naranja = np.array([30, 255, 255])
        bajo_amarillo = np.array([20, 50, 150])
        alto_amarillo = np.array([60, 255, 255])
        bajo_azul = np.array([90, 100, 100])
        alto_azul = np.array([120, 255, 255])

        # Creamos las máscaras para cada rango de color
        mascara_contorno = cv2.bitwise_or(atmc, atgc)
        mask_rojo1 = cv2.inRange(hsv_frame, bajo_rojo1, alto_rojo1)
        mask_rojo2 = cv2.inRange(hsv_frame, bajo_rojo2, alto_rojo2)
        mask_naranja = cv2.inRange(hsv_frame, bajo_naranja, alto_naranja)
        mask_amarillo = cv2.inRange(hsv_frame, bajo_amarillo, alto_amarillo)
        mask_azul = cv2.inRange(hsv_frame, bajo_azul, alto_azul)

        # Combinamos las máscaras
        mascara = cv2.bitwise_or(mask_rojo1, mask_rojo2, mask_naranja, mask_amarillo)
        mascara = cv2.bitwise_or(mask_azul, frame3, mascara, mascara_contorno)

        # Aplicamos operaciones morfológicas para eliminar el ruido
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        # Encontramos contornos en la máscara
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Dibujamos contornos y calculamos el área iluminada
        area_iluminada = 0
        for contorno in contornos:
            area_iluminada += cv2.contourArea(contorno)
            cv2.drawContours(frame, [contorno], -1, (0, 255, 0), 2)

        return frame, area_iluminada

    def calcular_promedio_area(self, intervalo):
        # Inicializamos el área total como cero
        area_total = 0
        # Tomamos el tiempo de inicio
        inicio = time.time()
        
        # Capturamos fotogramas durante el intervalo de tiempo dado
        while time.time() - inicio < intervalo:
            ret, frame = self.cap.read() # Capturamos un fotograma desde la cámara
            if not ret:
                print("Error al capturar el fotograma.")
                self.pausa = True

            frame, area = self.detectar_iluminacion(frame) # Detectamos la iluminación en el fotograma
            area_total += area # Sumamos el área iluminada al área total

            # Capturamos fotogramas durante el intervalo de tiempo dado
            cv2.imshow('Imagen en tiempo real', frame)

            # No se puede dividir entre 0 (numerador).
            if area_total == 0:
                area_total = intervalo

        # Devolvemos el promedio del área total
        return area_total / intervalo 
   
    def ejecutar(self):

        # Contador y cambio de área en 0's
        contador = 0
        cambio_area = 0

        # Mandamos a llamar a las variables necesarias
        tiempo_area_prom, porcentaje, num_alertas = self.configurar_parametros()

        while True:
            # Calculamos el promedio de área durante n cantidad de segundos
            promedio_actual = self.calcular_promedio_area(tiempo_area_prom) 

            # Calculamos el cambio de área si ya tenemos un promedio anterior
            if self.promedio_anterior != 0:
                cambio_area = abs((promedio_actual - self.promedio_anterior) / self.promedio_anterior) * 100
                print(promedio_actual)
            print(f"Cambio de área: {cambio_area: .2f}%")

            ## Entre mayor sea el porcentaje, mayor debe ser el el periodo de tiempo en segundos y viceversa, linea actual-9 Alt+g
            # Emitimos una alerta si el cambio de área es mayor al 5%,
            if cambio_area > porcentaje:  # Se cambia el porcentaje según las necesidades del momento
                #cambia el numero de alertas enviados
                if contador < num_alertas: 
                    # Agregar la fecha y hora al mensaje
                    fecha_hora_actual = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    mensaje = "¡Posible incendio forestal detectado!"
                    mensaje_alerta = f"{fecha_hora_actual}: {mensaje}"
##                    self.enviar_alerta(mensaje_alerta)
                    print(mensaje_alerta)
                    contador = contador + 1
                elif contador == num_alertas:
                    pivote = (tiempo_area_prom + num_alertas) / tiempo_area_prom
                    contador = (contador * 10 * pivote) - 1
                elif contador >= num_alertas:
                    contador = contador - num_alertas*pivote
                elif contador <= 0:
                    contador = 0

            # Actualizamos el promedio anterior con el actual
            self.promedio_anterior = promedio_actual

            # Detectar la tecla 'p' para pausar/reanudar el programa y detectamos la tecla 'q' para salir
            key = cv2.waitKey(10) & 0xFF
            if key == ord('q'):
                print("Saliendo del programa...")
                self.cap.release()
                cv2.destroyAllWindows()
                break
            elif key == ord('p'):
                while self.pausa:
                    if cv2.waitKey(10) & 0xFF == ord('p'):
                        print("Reanudando programa...")
                    elif cv2.waitKey(10) & 0xFF == ord('q'):
                        print('Saliendo...')
                        break
                
    def configurar_parametros(self):
        tiempo_area_prom = float(input("Ingrese el tiempo de promedio en segundos para calcular el área promedio: "))
        porcentaje = float(input("Ingrese el porcentaje de cambio de área: "))
        num_alertas = int(input("Ingrese el número máximo de alertas a enviar: "))
        return tiempo_area_prom, porcentaje, num_alertas
       
def menu():
    print("\nProyecto de programación")
    print("Visión por computadora 2024")
    print("Diego Armando Hernandez Ramos 1711196-6 6°7")
    print("Axel Reggy Perez Francisco 1712017-9 6°5")
    print("Francisco Javier Vargas Lara 2012484-1 6°7")
    print(" -----------------------------------------")
    print("1. Inicializar programa")
    print("2. Configurar parametros de captura y tratamiento de imagenes")
    print("0. Salir")

if __name__ == "__main__":
    idet = IluminacionDetectada()
    opcion = None

    while opcion != "0":
        menu()
        opcion = input("Ingrese su opción: ")

        if opcion == "1":
            idet.ejecutar()
        elif opcion == "2":
            idet.configurar_parametros()
        elif opcion == "0":
            print("Saliendo del programa...")
        else:
            print("Opcion no valida. Intente de nuevo")

            
