from xml.dom import minidom
import xml.sax

xml_parser = xml.sax.make_parser()
orig_set_content_handler = xml_parser.setContentHandler

def set_content_handler(dom_handler):
    global orig_set_content_handler

    def startElementNS(name, tagName , attrs):
        orig_start_cb(name, tagName, attrs)
        cur_elem = dom_handler.elementStack[-1]
        cur_elem.parse_position = (xml_parser._parser.CurrentLineNumber, xml_parser._parser.CurrentColumnNumber)

    orig_start_cb = dom_handler.startElementNS
    dom_handler.startElementNS = startElementNS
    orig_set_content_handler(dom_handler)

xml_parser.setContentHandler = set_content_handler

def getText(el):
    rc = []
    for node in el.childNodes:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def parse(file):
	return minidom.parse(file, xml_parser)
