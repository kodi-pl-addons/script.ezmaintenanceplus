# coding=utf-8
# Module: advancedsettings
# Author: Alex Bratchik
# Created on: 20.05.2021
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import hashlib
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from math import trunc
import re

import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

ADSFNAME = "advancedsettings.xml"
SRCFNAME = "settings.src.xml"
PLGFNAME = "settings.xml"
BACKNAME = "settings.backup.xml"

class AdvancedSettings():
    def __init__(self):
        self.id = "script.ezmaintenanceplus"
        self.addon = xbmcaddon.Addon(self.id)
        self.path = self.addon.getAddonInfo('path')
        self.ads_path = xbmcvfs.translatePath("special://userdata")
        self.data_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))

        self.language = self.addon.getLocalizedString

        self.ads_file = os.path.join(self.ads_path, ADSFNAME)
        self.sts_file = os.path.join(self.data_path, PLGFNAME)
        self.plg_file = os.path.join(os.path.join(self.path, "resources"), PLGFNAME)
        self.plb_file = os.path.join(os.path.join(self.path, "resources"), BACKNAME)

        self.plg_settings = None
        self.adv_settings = None

    def unlock(self):        
        srcfname = os.path.join(os.path.join(self.path, "resources"), SRCFNAME)

        with open(self.plg_file, "r") as file:
            data = file.read()

        if "id=\"maintenance\"" in data:
            xbmc.sleep(5)
            xbmcvfs.copy(self.plg_file, self.plb_file)

            xbmc.sleep(1)
            xbmcvfs.copy(srcfname, self.plg_file)
            xbmc.sleep(1)

        self.plg_settings = self._load_xml_from_file(self.plg_file)
        try:
            self.adv_settings = self._load_xml_from_file(self.ads_file)
            # self.gui_settings = self._load_xml_from_file(self.gui_file)
        except ET.ParseError:
            xbmcgui.Dialog().notification(self.addon.getAddonInfo("name"), "%s %s" % (self.language(30800), ADSFNAME), xbmcgui.NOTIFICATION_ERROR, 5000)

        self._load()
        self.addon.openSettings(self.id)
        
        ret = self._save(self.addon, self.ads_file)

        if ret:
            xbmcgui.Dialog().notification(self.addon.getAddonInfo("name"), self.language(30802), xbmcgui.NOTIFICATION_INFO, 5000)

        xbmcvfs.copy(self.plb_file, self.plg_file)

    def _load(self):
        for cat in self.plg_settings.findall(".//*category"):
            for group in cat.findall("group"):
                for s in group.findall("setting[@id]"):
                    setting_id = s.attrib['id']
                    self.addon.setSetting(setting_id, self._read_adv_setting_value(cat, s))

    def _save(self, addon, path):
        if self.adv_settings is None:
            self.adv_settings = ET.fromstring("<advancedsettings version='1.0' />")

        for cat in self.plg_settings.findall(".//*category"):
            for group in cat.findall("group"):
                for s in group.findall("setting[@id]"):
                    setting_id = s.attrib['id']
                    value = self.addon.getSetting(setting_id)

                    self._save_adv_setting_value(cat, s, value)

                # remove empty categories
                adv_cat = self.adv_settings.find(cat.attrib['id'])
                if not (adv_cat is None) and len(adv_cat) == 0:
                    self.adv_settings.remove(adv_cat)

        self._backup_file(self.ads_file)
        ret = self._save_pretty_xml(self.adv_settings, self.ads_file, addon, path)

        return ret

    def _save_adv_setting_value(self, cat, s, value):
        xbmc.log("Category %s, setting %s" % (cat.attrib['id'], s.attrib['id']), xbmc.LOGDEBUG)

        default = s.get('default') if 'default' in s.attrib else (s.find("default").text or '')

        section_tag = cat.attrib['id'] # category
        section = self.adv_settings if self._is_root_cat(cat) else self.adv_settings.find(section_tag)
        if section is None:
            section = ET.SubElement(self.adv_settings, section_tag)

        setting_tag = s.attrib['id'].partition("#")[0] # id name

        setting = self._lookup_element(section, setting_tag) 
        #section.find(setting_tag)

        if default == value:
            if not (setting is None):
                if "#" in s.attrib['id']:
                    attrib = s.attrib['id'].partition("#")[2]
                    if attrib in setting.attrib:
                        setting.attrib.pop(attrib)
                    if setting.text == "":
                        self._remove_element(section, setting_tag)
                else:
                    if len(setting.attrib) == 0:
                        self._remove_element(section, setting_tag)
            return

        if setting is None:
            setting = self._create_element(section, setting_tag)
            # ET.SubElement(section, setting_tag)

        self._write_setting_value(setting, s, self._encode_value(value, s))

        xbmcvfs.copy(self.plb_file, self.plg_file)

    def _read_adv_setting_value(self, cat, s):
        xbmc.log("Category %s, setting %s" % (cat.attrib['id'], s.attrib['id']), xbmc.LOGDEBUG)
        if self.adv_settings is None:
            xbmc.log("%s not found" % ADSFNAME, xbmc.LOGDEBUG)
            return self._get_gui_setting_value(cat, s)

        section_tag = cat.attrib['id']
        section = self.adv_settings if self._is_root_cat(cat) else self.adv_settings.find(section_tag)
        if section is None:
            xbmc.log("Section %s not found" % section_tag, xbmc.LOGDEBUG)
            return self._get_gui_setting_value(cat, s)

        setting = self._lookup_element(section, s.attrib['id'].partition("#")[0])
        # section.find(s.attrib['id'].partition("#")[0])
        if not (setting is None):
            return self._decode_value(self._read_setting_value(setting, s), s)
        else:
            xbmc.log("Setting %s not found" % s.attrib['id'], xbmc.LOGDEBUG)
            return self._get_gui_setting_value(cat, s)

    def _get_gui_setting_value(self, cat, s):
        # setting_id = "%s.%s" % (cat.attrib['id'], s.attrib['id'])
        default = s.get('default') if 'default' in s.attrib else (s.find("default").text or '')

        return default

    def _lookup_element(self, parent, path):
        if parent is None:
            return None

        pathelem = path.split("/")
        if parent.tag == pathelem[0]:
            pathelem[0] = pathelem[1]
            path = pathelem[1]

        if len(pathelem) == 1:
            if "$" in path:
                name_index = path.split("$")
                elements = parent.findall(name_index[0])
                index = int(name_index[1])
                if index < len(elements):
                    return elements[index]
                else:
                    return None
            else:
                return parent.find(path) 
        else:
            return self._lookup_element(parent.find(pathelem[0]), "/".join(pathelem[1:]))

    def _create_element(self, parent, path):
        pathelem = path.split("/")
        if len(pathelem) == 1:
            if "$" in path:
                name_index = path.split("$")
                xbmc.log("Create element %s.%s" % (parent.tag, name_index[0]))
                return ET.SubElement(parent, name_index[0])
            else:
                return ET.SubElement(parent, path)
        else:
            subparent = parent.find(pathelem[0])
            if subparent is None:
                subparent = ET.SubElement(parent, pathelem[0])
            return self._create_element(subparent, "/".join(pathelem[1:]))

    def _remove_element(self, rootparent, path):
        elem = self._lookup_element(rootparent, path)
        if elem is None:
            return
        pathelem = path.split("/")
        l = len(pathelem)
        if l == 1:
            rootparent.remove(elem)
        else:
            parentpath = "/".join(pathelem[0:l-1])
            parent = self._lookup_element(rootparent, parentpath)
            if "$" in pathelem[l-1]:
                name_index = pathelem[l-1].split("$")
                index = int(name_index[1])
                #xbmc.log("Remove teg %s.%s-%s" % (parent.tag, name_index[0], name_index[1]), xbmc.LOGDEBUG)
                if index < len(parent):
                    del parent[index:]
                #xbmc.log("new num of children %s" % len(parent), xbmc.LOGDEBUG)
            else:
                parent.remove(elem)
            if len(parent) == 0 and len(parent.attrib) == 0:
                self._remove_element(rootparent, parentpath)

    @staticmethod
    def _get_file_hash(filename):
        if xbmcvfs.exists(filename):
            with open(filename, 'r+') as f:
                return hashlib.md5(f.read().encode('utf-8')).hexdigest()
        else:
            return ""

    @staticmethod
    def _is_root_cat(cat):
        return 'parent' in cat.attrib and cat.attrib['parent'] == "true"

    @staticmethod
    def _decode_value(value, s): 
        if s.attrib['help'] == "enum":
            constraints = s.find(".//*option")
            if constraints is None:
                return value
            else:
                return constraints.text
        else:
            return value

    @staticmethod
    def _encode_value(value, s):
        if s.attrib['help'] == "enum":
            constraints = s.find(".//*option")
            if constraints is None:
                return value
            else:
                return constraints.attrib['label'] if not constraints.attrib['label'] == "none" else ""
        else:
            return value

    @staticmethod
    def _read_setting_value(setting, s):
        if "#" in s.attrib['id']:
            idc = s.attrib['id'].split("#")
            xbmc.log("Setting attribute %s of setting  %s" % (idc[1], s.attrib['id']))
            if idc[1] in setting.attrib:
                return setting.attrib[idc[1]]
            else:
                default = s.get('default') if 'default' in s.attrib else (s.find("default").text or '')
                return default
        else:
            return setting.text

    @staticmethod
    def _write_setting_value(setting, s, value):
        if "#" in s.attrib['id']:
            idc = s.attrib['id'].split("#")
            xbmc.log("Setting attribute %s of setting  %s" % (idc[1], s.attrib['id']))
            setting.set(idc[1], value)
        else:
            setting.text = value

    @staticmethod
    def _set_child_text(element, child_tag, value):
        child = element.find(child_tag)
        if not (child is None):
            child.text = value

    @staticmethod
    def _load_xml_from_file(filename):
        if xbmcvfs.exists(filename):
            tree = ET.parse(filename)
            return tree.getroot()
        else:
            return None

    @staticmethod
    def _save_pretty_xml(element, output_xml, addon, path):
        try:
            with open(output_xml, "r") as file:
                read_xml_string = file.read()
        except:
            read_xml_string = ''

        xml_string = minidom.parseString(ET.tostring(element)).toprettyxml()
        xml_string = "".join([s for s in xml_string.splitlines(True) if s.strip()])

        if xml_string == read_xml_string:
            return False

        AdvancedSettings._mem_check(addon, path, output_xml, xml_string)    

    @staticmethod
    def _mem_check(addon, path, output_xml, xml_string):
        MEM        =  xbmc.getInfoLabel("System.Memory(total)")
        FREEMEM    =  xbmc.getInfoLabel("System.FreeMemory")

        BUFFER_F   =  re.sub('[^0-9]','',FREEMEM)
        BUFFER_F   = int(BUFFER_F) / 3
        BUFFERSIZE = trunc(BUFFER_F * 1024 * 1024)

        B = str(BUFFERSIZE)

        boolean_regex = re.compile('<optimized>true</optimized>')
        mem_regex = re.compile('<memorysize>\d+</memorysize>')

        if not mem_regex.findall(xml_string):
            if boolean_regex.findall(xml_string):
                xml_string = re.sub('<optimized>true</optimized>', '<optimized>true</optimized>\n\t\t<memorysize>{0}</memorysize>'.format(B), xml_string)
                
            elif not boolean_regex.findall(xml_string):
                xml_string = re.sub('<memorysize>\d+</memorysize>', '<memorysize>{0}</memorysize>'.format(B), xml_string)

        else:
            if boolean_regex.findall(xml_string):
                xml_string = re.sub('\n\t\t<memorysize>\d+</memorysize>', '', xml_string)
                xml_string = re.sub('<optimized>true</optimized>', '<optimized>true</optimized>\n\t\t<memorysize>{0}</memorysize>'.format(B), xml_string)

        ret = xbmcgui.Dialog().yesno(addon.getAddonInfo("name"), addon.getLocalizedString(30801))
        if ret:
            with open(output_xml, "w") as file_out:
                file_out.write(xml_string)
                return True
        else:
            return False

    @staticmethod
    def _backup_file(fpath):
        if xbmcvfs.exists(fpath):
            fpathbak = "%s.bak" % fpath
            if xbmcvfs.exists(fpathbak):
                xbmcvfs.delete(fpathbak)
            return xbmcvfs.copy(fpath, fpathbak)
        else:
            return False


