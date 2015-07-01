import collections
import cxexml
import copy

from constants import *

class SchemaElement:
    def __init__(self, name):
        self.name = name
        self.children = collections.OrderedDict()
        self.optional = False
        self.repeatable = False
        self.type = DType.STRING

    # can return None if it breaks, else returns schema element object
    @staticmethod
    def from_xml(root, element_name, defns={}, minOccurs="1", maxOccurs="1"):
        if root == None:
            crash("Schema error: no root element found?\n")
            return None

        if defns == {}:
            for el in root.getElementsByTagName("ElementType"):
                defns[el.getAttribute("name")] = el

            if defns == {}:
                #FIXME this shouldn't be a crash but i'm lazy
                crash("Schema error: No ElementType definitions found in schema!")
                return None

        el = defns[element_name]

        if el == None:
            error("Schema error: no ElementType found for %s, ignoring\n" % (element_name))
            return None

        se = SchemaElement(element_name)

        for subel in el.getElementsByTagName("element"):
            subtype = subel.getAttribute('type')
            mi = subel.getAttribute('minOccurs')
            ma = subel.getAttribute('maxOccurs')
            se.children[subtype] = SchemaElement.from_xml(root, subtype, defns, minOccurs=mi,
                maxOccurs=ma)

        if len(se.children) != 0:
            se.type = DType.COMPLEX
        else:
            datatype = el.getAttribute('dt:type')
            if datatype != None and datatype != '':
                if datatype == 'int':
                    se.type = DType.INTEGER
                elif datatype == 'boolean':
                    se.type = DType.BOOLEAN
                else:
                    error("Schema error: unknown datatype '%s'" % datatype)

        if minOccurs == "0":
            se.optional = True

        if maxOccurs == "*":
            if element_name == 'Button':
                # ignore, someone at firaxis is crazy
                pass
            else:
                se.repeatable = True

        return se


    def __repr__(self, indent=''):
        s = "" #"<SchemaElement %s " % self.name
        if self.optional:
            s += " (opt)"
        if self.repeatable:
            s += " (rep)"
        if len(self.children) != 0:
            s += "<\n"
            indent += '    '
            for (k,v) in self.children.items():
                if (type(v) == type(self)):
                    s += indent + k + ": " + v.__repr__(indent) + "\n"
                else:
                    s += indent + k + ": " + v.__repr__() + "\n"
            indent = indent[:-4]
            s += indent + ">"
        else:
            s += " " + self.type #+ ">"
        return s

    # obj must not be a list
    def write_into_element(self, doc, element, obj):
        value = None
        name = self.name

        if obj == None:
            return True

        if element.tagName != name:
            error("Internal XML write error: mismatched schema and element (%s)." % (name,))

        if self.type == DType.STRING:
            if obj == None:
                value = ""
            else:
                value = str(obj)
        elif self.type == DType.INTEGER:
            if obj == None:
                value = "0"
            else:
                value = str(int(obj))
        elif self.type == DType.BOOLEAN:
            if obj == None:
                value = "0"
            else:
                value = str(int(bool(obj)))

        if value != None:
            textnode = doc.createTextNode(value)
            element.appendChild(textnode)
            return True

        if self.type != DType.COMPLEX:
            error("Internal XML write error: unhandled dtype %s for %s" 
                % (self.type,self.name))
            return False

        # otherwise, obj must be an Item

        if not isinstance(obj, Item):
            raise ArgumentError("obj must be Item at this point")

        for (subname, subvalue) in obj.items():
            subschema = self.children[subname]

            if not isinstance(subvalue, list):
                subvalue = [subvalue]

            for v in subvalue:
                subel = doc.createElement(subname)
                success = subschema.write_into_element(doc, subel, v)
                if not success:
                    return False
                if subschema.optional and not subel.hasChildNodes():
                    continue
                else:
                    element.appendChild(subel)

        return True


    # returns true (success) or false.
    def read_into_item(self, element, obj):
        value = None
        name = self.name

        if element.tagName != name:
            error("Internal XML read error: mismatched schema and element (%s) at line %i, char %i." % (name,)+element.parse_position)
            return False

        try:
            body = cxexml.getText(element)
            if self.type == DType.STRING:
                value = body
            elif self.type == DType.INTEGER:
                if body == "":
                    value = 0
                else:
                    value = int(body)
            elif self.type == DType.BOOLEAN:
                if body == "":
                    value = False
                else:
                    value = bool(int(body)) # bool("0") is True, so cast to int first
        except ValueError, e:
            error("XML error: can't parse value in %s at line %i: %s" %
                 (self.name, element.parse_position[0], e))
            return False

        if value != None:
            if self.repeatable:
                if name in obj:
                    obj[name].append(value)
                else:
                    obj[name] = [value]
                return True
            else:
                if name in obj:
                    if not self.repeatable:
                        error(("XML error: can only be 1 max occurrence of '%s' as a subelement, but found " 
                         + " multiple at line %i") % (self.name, element.parse_position[0]))
                        return False
                else:
                    obj[name] = value
                    return True

        if self.type != DType.COMPLEX:
            if self.optional:
                return True
            else:        
                error("XML error: '%s' is required in the schema, but no value was found in the tag (line %i, char %i)" 
                    % (name,)+element.parse_position)
                return False

        # otherwise...

        value = Item(name)
        value.schema = self
        
        e = element.firstChild

        while e != None:
            if e.nodeName in self.children:
                subschema = self.children[e.nodeName]
                
                success = subschema.read_into_item(e, value)

                if not success:
                    return False

            e = e.nextSibling


        if self.repeatable:
            if isinstance(obj, list):
                # idk
                obj.append(value)
            elif name in obj:
                obj[name].append(value)
            else:
                #sys.stderr.write("%s[%s] = %s\n" % (obj, name, value))
                obj[name] = [value]
            return True
        else:
            if name in obj:
                if not self.repeatable:
                    error("XML error: can only be 1 max occurrence of '%s' as a subelement, but found " 
                     + " multiple at line %i" % (self.name, element.parse_position[0]))
                    return False
            else:
                obj[name] = value
                return True

class Item(collections.MutableMapping):

    def __init__(self, name):
        self.internal_dict = collections.OrderedDict()
        self.change_set = set()
        self.changed = False
        self.name = name

    def __deepcopy__(self, memo):
        other = Item(self.name)
        other.changed = True
        other.internal_dict = copy.deepcopy(self.internal_dict, memo)
        return other

    def set_saved(self):
        self.changed = False
        self.change_set = set()

    def __getitem__(self, key):
        return self.internal_dict.__getitem__(key)

    def __setitem__(self, key, val):
        return self.internal_dict.__setitem__(key, val)

    def __delitem__(self, key):
        return self.internal_dict.__delitem__(key)

    def __len__(self):
        return self.internal_dict.__len__()

    def __contains__(self, key):
        return self.internal_dict.__contains__(key)

    def __iter__(self):
        return self.internal_dict.__iter__()

    def __repr__(self):
        return ("<%s>" % self.name) + self.internal_dict.__repr__()
