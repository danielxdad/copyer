# -*- coding: utf-8 -*-
from xml.etree import ElementTree as ET
import os, urllib, win32api, win32file, gzip, bz2, datetime, types

__all__ = ('FSXMLTree', )

def stat_time_iso_time(stat_time):
    if type(stat_time) in [types.IntType, types.LongType]:
        return datetime.datetime.fromtimestamp(stat_time).isoformat()
    return '<!empty>'

class FSXMLTree(object):
    def get_drives_from_types(self, types):
        """Devuelve una lista con las volumenes dependiendo de el tipo especificado como parametro"""
        ret_list = []
        for d in win32api.GetLogicalDriveStrings().split('\x00')[:-1]:
            #Quitamos los volumenes A y B, reservadas para las disqueteras
            if d not in ['A:\\', 'B:\\'] and (win32file.GetDriveType(d) in types) and os.path.ismount(d):
                ret_list.append(d)
        return ret_list
    
    """
    def patch_xmlpath(self, path):
        path_elements = path.split('/')
        for pathel in path_elements:
            if len(pathel):
                if not pathel[0].isalnum():
                    path_elements[path_elements.index(pathel)] = '%' + hex(ord(pathel[0]))[2:].upper() + pathel[1:]
        return string.join(path_elements, '/')
    """

    def _iter_child(self, sub_elements, path_comp):
        for subelement in sub_elements:
            if subelement.tag == 'dir':
                try:
                    index = path_comp.index(subelement.text)
                except:
                    pass
                else:
                    if index == 0:
                        path_comp.pop(0)
                        if not path_comp:
                            return subelement
                        return self._iter_child(list(subelement), path_comp)
    
    
    def make_tree(self):
        self.root = ET.Element('root')
        self.root.attrib['id'] = str(self._id_counter)
        self._id_counter += 1
        for drive in self.drives:
            print 'Fetching %s...' % (drive)
            
            ET.SubElement(self.root, 'dir').text = urllib.quote(drive[:2])
            
            for dirpath, dirs, files in os.walk(drive):
                path_components = [urllib.quote(comp) for comp in dirpath.split('\\') if comp]
                
                #print path_components
                curr_dir_element = self._iter_child(self.root, path_components)
                
                if curr_dir_element == None:
                    raise ValueError('Not found path to element: %s' % (dirpath))
                
                curr_dir_element.attrib['dirs'] = str(len(dirs))
                curr_dir_element.attrib['files'] = str(len(files))
                if curr_dir_element.attrib.get('id', None) == None:
                    curr_dir_element.attrib['id'] = str(self._id_counter)
                    self._id_counter += 1
                
                #Dirs
                for name in dirs:
                    subdir = ET.SubElement(curr_dir_element, 'dir')
                    subdir.text = urllib.quote(name)
                    subdir.attrib['id'] = str(self._id_counter)
                    self._id_counter += 1
                
                #Files
                for name in files:
                    path = os.path.join(dirpath, name)
                    try:
                        stat = os.stat(path)
                    except OSError as (errno, strerr):
                        print 'Error obteniendo informacion del fichero \"%s\": %d - %s' % (path, errno, strerr)
                    else:
                        ET.SubElement(curr_dir_element, 'file', {'id': str(self._id_counter), 'size': str(stat.st_size), \
                        'atime': stat_time_iso_time(stat.st_atime), 'mtime': stat_time_iso_time(stat.st_mtime), \
                        'ctime': stat_time_iso_time(stat.st_ctime)}).text = urllib.quote(name)
                        self._id_counter += 1
                        
        self.tree_was_make = True
        
        
    def to_xml(self):
        if self.root is None:
            self.make_tree()
        return ET.tostring(self.root, encoding='utf-8')
    
    
    def to_file(self, filename, compression=None):
        if not filename:
            raise TypeError('Invalid argument')
        
        if self.root is None:
            self.make_tree()
            
        if compression is not None and compression not in self.valid_compression:
            raise ValueError('Invalid compression')
        
        if compression == 'gz':
            fd = gzip.GzipFile(os.path.split(filename)[1], fileobj=open(filename + '.' + compression, 'wb'))
        elif compression == 'bz2':
            fd = bz2.BZ2File(filename + '.' + compression, 'wb')
        else:
            fd = open(filename, 'wb')
            
        ET.ElementTree(self.root).write(fd, encoding='utf-8', xml_declaration=True)
        fd.close()

        
    def __init__(self, exclude_drives=[], drive_types=[win32file.DRIVE_FIXED, win32file.DRIVE_REMOVABLE]):
        os.stat_float_times(False)
        self.valid_compression = ['gz', 'bz2']
        self.root = None
        self.drives = [d for d in self.get_drives_from_types(drive_types) if d not in exclude_drives]
        self._id_counter = 0
        

#fs_xml_tree = FSXMLTree()
#fs_xml_tree = FSXMLTree(exclude_drives=['C:\\', 'G:\\'], drive_types=[win32file.DRIVE_FIXED])
#fs_xml_tree = FSXMLTree(drive_types=[win32file.DRIVE_REMOVABLE])
#fs_xml_tree.to_file('output.xml')
