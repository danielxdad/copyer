# -*- coding: utf-8 -*-
import sys, os, re, win32api, win32file, win32process, tarfile, ConfigParser, random, logging, platform, atexit
from datetime import datetime

CONFIG_FILE = 'copyer.ini'
Config = None 
logger = None
ret_status_code = 0

class Configuration:
    """
    Obtiene e interpreta la configuracion del archivo copyer.ini, ademas de implementar la validacion
    de si el archivo sera o no copiado"""
    def __init__(self):
        self.config = None
        self.especificExtConfig = {}
        self.copy_from = None
        self.ignore_current_drive = True
        self.compression = ''
        self.LST_INCLUDE_FILES_EXTENSIONS = []
        self.MAX_FILE_SIZE_TO_COPY = 0
        self.ignore_path_patterns = []
        self.success_beep = False
        self.error_beep = False
        
        
    def readConfig(self, configFile):
        try:
            fd = open(configFile)
        except IOError as (errn, strerr):
            logger.error('Error al abrir el archivo de configuracion: %d - %s' % (errn, strerr))
            self.config = None
            return False
            
        self.config = ConfigParser.RawConfigParser()
        
        try:
            self.config.readfp(fd)
        except:
            logger.error('Error al intentar leer el archivo de configuracion')
            self.config = None
            return False
         
        try:
            nameValues = self.config.items('global')
        except:
            logger.error('Error leyendo el archivo de configuracion: no existe la seccion "global"')
            self.config = None
            return False
        
        self.output_dir = '.' + os.sep
        for name, value in nameValues:
            if name == 'max_file_size':
                self.MAX_FILE_SIZE_TO_COPY = int(value)
            
            elif name == 'include_files_extensions':
                self.LST_INCLUDE_FILES_EXTENSIONS = set(value.replace(' ', '').lower().split(','))
            
            elif name == 'copy_from':
                self.copy_from = value
            
            elif name == 'ignore_current_drive':
                self.ignore_current_drive = bool(int(value))
            
            elif name == 'compression' and value in ['gz', 'bz2']:
                self.compression = value
            
            elif name == 'output_dir' and value:
                self.output_dir = value
            
            elif name == 'success_beep' and value.lower() not in ['0', 'false']:
                self.success_beep = True
            
            elif name == 'error_beep' and value.lower() not in ['0', 'false']:
                self.error_beep = True
            
            elif name == 'ignore_path_patterns' and value:
                for e in value.split(','):
                    if re.match('%[\S]*%$', e):
                        try: t = os.environ[e[1: -1]]
                        except KeyError: logger.warn('La variable de entorno especificada como patron no existe: %s' % (e))
                        else: self.ignore_path_patterns.append(t)
                    else:
                        self.ignore_path_patterns.append(e)

        for ext in self.LST_INCLUDE_FILES_EXTENSIONS:
            try:
                self.especificExtConfig[ext] = self.config.items(ext)
            except ConfigParser.NoSectionError:
                continue
            except:
                logger.error('Error leyendo el archivo de configuracion')
                self.config = None
                return False
                
        return True
        
        
    def filePassRestriction(self, filename):
        #Comprobacion segun los patrones especificado que se deben ignorar
        for value in self.ignore_path_patterns:
            if filename.find(value) != -1:
                return False
        
        #Comprobacion por si es un directorio
        if os.path.isdir(filename):
            return True
            
        #Comprobacion especifica segun la extencion del archivo
        if os.path.splitext(filename)[1].lower() in self.especificExtConfig:
            for name, value in self.especificExtConfig[os.path.splitext(filename)[1].lower()]:
                if name.lower() == 'max_file_size':
                    if os.path.getsize(filename) > int(value):
                        return False
                    
                if name.lower() == 'rand_copy_percent' and int(value):
                    return not bool(random.randint(0, 100/int(value)-1))   

        #Comprobacion segun el tamano del archivo desde la configuracion global, 
        #la lista de extesiones permitidas, o si carece de ella
        try:
            if os.path.getsize(filename) <= self.MAX_FILE_SIZE_TO_COPY:
                if os.path.splitext(filename)[1].lower() in self.LST_INCLUDE_FILES_EXTENSIONS \
                or len(os.path.splitext(filename)[1]) == 0:
                    return True
        except WindowsError: pass
        
        return False

#----------------------------------------------------------------------------------------------------------------------------
def isVolumeMount(volume):
    """
    Determina cuando un volumen se encuentra montado y puede ser leido, 
    si no se hace esta comprobacion el programa presentara problemas, como por ejemplo con los lectores
    de tarjetas, dado que las torres existes pero al no tener tarjetas estan desmontadas"""
    FILE_EXECUTE = 0x20
    INVALID_HANDLE_VALUE = -1
    
    if not volume: return False
    
    tmpVol = '\\\\.\\' + volume
    if tmpVol[-1] == '\\': tmpVol = tmpVol[:-1]
    
    hVolume = win32file.CreateFile(tmpVol, FILE_EXECUTE, \
    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE, None, win32file.OPEN_EXISTING, 0, 0)
    
    if hVolume == INVALID_HANDLE_VALUE: 
        return False

    try:
        ret = win32file.DeviceIoControl(hVolume, 0x90028, None, 0, None)
    except:
        win32file.CloseHandle(hVolume)
        return False
    else:
        win32file.CloseHandle(hVolume)
        return not bool(win32api.GetLastError())
        
    
def getDrivesFromType(type):
    """
    Devuelve una lista con las volumenes dependiendo de el tipo especificado como parametro
    """
    ret_list = []
    
    for d in win32api.GetLogicalDriveStrings().split('\x00')[:-1]:
        #Quitamos los volumenes A y B, reservadas para las disqueteras
        if d not in ['A:\\', 'B:\\'] and win32file.GetDriveType(d) == type and isVolumeMount(d):
            ret_list.append(d)
    
    return ret_list

    
def ignoreCopyPatterns(filename):
    """
    Esta se pasa como parametro a la funcion add de un objeto tar y devuelve si el archivo sera o no incluido
    el en archivo dependiendo de la configuracion"""
    global Config
    
    return not Config.filePassRestriction(filename)

    
def getLogger():
    """
    Inicia un objeto Logger, para imprimir mensaje en el archivo de logs
    """
    global logger
    logger = logging.getLogger('copyer')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    

def printPlatformInfo():
    """
    Imprime informacion basica sobre el OS/PC en que es ejecutado
    """
    info = platform.uname()
    logger.info('%s %s %s %s - %s - %s' % (info[0], info[2], info[3], info[4], info[1], info[5]))


@atexit.register
def atExitHandle():
    if ret_status_code == 0 and Config.success_beep:
        win32api.Beep(1500, 500)
    elif ret_status_code != 0 and Config.error_beep:
        win32api.Beep(4000, 750)
        

def main():
    global Config
    
    getLogger()
    
    logger.info('Copyer a comenzado')
    printPlatformInfo()
    
    win32api.SetErrorMode(0x0001 or 0x8000)
    
    Config = Configuration()
    if not Config.readConfig(CONFIG_FILE):
        ret_status_code = 1
        return ret_status_code
    
    #Obtener lista de unidades segun la configuracion
    if Config.copy_from == 'all':
        lstDrives = getDrivesFromType(win32file.DRIVE_FIXED) + getDrivesFromType(win32file.DRIVE_REMOVABLE)
    elif Config.copy_from == 'hd':
        lstDrives = getDrivesFromType(win32file.DRIVE_FIXED)
    elif Config.copy_from == 'fm':
        lstDrives = getDrivesFromType(win32file.DRIVE_REMOVABLE)
    else:
        logger.error('Error, el parametro "copy_from" es invalido, revise la configuracion')
        ret_status_code = 1
        return ret_status_code
        
    if not lstDrives:
        logger.warn('No hay unidades disponibles')
        ret_status_code = 1
        return ret_status_code
        
    driveCopyDest = win32process.GetModuleFileNameEx(win32process.GetCurrentProcess(), 0)[:3]
    
    if Config.ignore_current_drive:
        try:
            lstDrives.remove(driveCopyDest)
        except: pass
    
    if not os.path.exists(Config.output_dir):
        os.makedirs(Config.output_dir)
    
    for drive in lstDrives:
        pathCopyDest = os.path.join(Config.output_dir, datetime.now().strftime('%d-%m-%Y %H.%M.%S ' + drive[0] + '.tar'))
        
        if Config.compression == 'gz':
            pathCopyDest += '.gz'
        elif Config.compression == 'bz2':
            pathCopyDest += '.bz2'
    
        logger.info('Copiando desde %s a %s' % (drive, pathCopyDest))
        try:
            tarFile = tarfile.open(pathCopyDest, 'w:' + Config.compression, \
            ignore_zeros=True, encoding='utf-8', errors='ignore', debug=0)
        except: 
            typ,value,tb = sys.exc_info()
            logger.error('Error al crear el archivo de destino %s: %s - %s' % (pathCopyDest, repr(typ), repr(value)))
            continue

        #Se evita el uso de la function TarFile.add, donde que al tener establecido el parametro recursive a True
        #y suceder un excepcion en el proceso, por ejemplo, un 'Acceso denegado', termina la inclusion de archivos
        for root, dirs, files in os.walk(drive):
            for name in dirs:
                subdir = os.path.join(root, name)
                if ignoreCopyPatterns(subdir):
                    del dirs[dirs.index(name)]
                
            for name in files:
                filename = os.path.join(root, name)
                if not ignoreCopyPatterns(filename):
                    try:
                        tarFile.add(filename, recursive=False)
                    except KeyboardInterrupt:
                        logger.error('El proceso se cerrara a peticion del usuario')
                        tarFile.close()
                        ret_status_code = 1
                        return ret_status_code
                    except:
                        typ,value,tb = sys.exc_info()
                        logger.error('Error al intentar agregar el archivo %s: %s - %s' % (filename, repr(typ), repr(value)))
        
        tarFile.close()
    
    logger.info('Copyer a terminado')
    ret_status_code = 0
    return ret_status_code
      
     
if __name__ == '__main__':
    #Redireccionamos la salida estandar y de error a un 'copyer.log', para guardar los logs.
    fd = open('copyer.log', 'a')
    sys.stdout = fd
    sys.stderr = fd
    sys.exit(main())
    