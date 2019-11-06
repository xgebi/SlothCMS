from xml.dom import minidom
from xml.dom.minidom import Node
import xml

from pathlib import Path
import os
from collections.abc import Iterable


def render_toe(*args, template, path_to_templates, **kwargs):
	if path_to_templates is None:
		return None

	toe_engine = Toe(path_to_templates, template, kwargs)
	return toe_engine.process_tree()

class Toe:
	tree = {}
	new_tree = {}
	path_to_templates = ""
	template_load_error = False
	variables = None
	current_scope = None

	def __init__(self, path_to_templates, template, data):
		self.path_to_templates = path_to_templates
		self.variables = Variable_Scope(data, None)
		self.current_scope = self.variables

		impl = minidom.getDOMImplementation()
		doctype = impl.createDocumentType('html', None, None) 
		self.new_tree = impl.createDocument(xml.dom.XHTML_NAMESPACE, 'html', doctype)

		for node in self.new_tree.childNodes:
			if node.nodeType == Node.ELEMENT_NODE:
				lang = self.current_scope.find_variable('lang')
				node.setAttribute('lang', lang if lang is not None else 'en')

		template_file = ""
		if template.endswith(".html") or template.endswith(".htm"):
			with open(os.path.join(path_to_templates, template)) as f:			
					template_file = str(f.read())
		else:
			self.template_load_error = True
			return

		self.tree = minidom.parseString(template_file)
		self.remove_blanks(self.tree)
		self.tree.normalize()
	
	def process_tree(self):
		# There can only be one root element
		if len(self.tree.childNodes) != 1:
			return None

		for node in self.tree.childNodes[0].childNodes:
			res = self.process_subtree(self.new_tree.childNodes[1], node)

			if res is not None:				
				self.new_tree.childNodes[1].appendChild(res)

		return self.new_tree.toxml()[self.new_tree.toxml().find('?>') + 2:]
	
	def process_subtree(self, new_tree_parent, tree):
		"""
		Params:
			new_tree_parent: Document or Node object
			tree: Document or Node object
		Returns
			Document or Node object
		"""
		if tree.nodeType == Node.TEXT_NODE:
			return self.new_tree.createTextNode(tree.wholeText)
			

		# check for toe tags
		if (tree.tagName.startswith('toe:')):
			return self.process_toe_tag(new_tree_parent, tree)

		# check for toe attributes
		attributes = dict(tree.attributes).keys()
		for attribute in attributes:
			if attribute == 'toe:if':
				return self.process_if_attribute(new_tree_parent, tree)				
			if attribute == 'toe:for':
				return self.process_for_attribute(new_tree_parent, tree)	
			if attribute == 'toe:while':
				return self.process_while_attribute(new_tree_parent, tree)			

		# append regular element to parent element
		new_tree_node = self.new_tree.createElement(tree.tagName)
		if tree.attributes is not None or len(tree.attributes) > 0:
			for key in tree.attributes.keys():
				new_tree_node.setAttribute(key, tree.getAttribute(key))

		for node in tree.childNodes:			
			res = self.process_subtree(new_tree_node, node)

			if type(res) is list:
				for temp_node in res:
					new_tree_node.appendChild(temp_node)	
			if res is not None:
				new_tree_node.appendChild(res)

		return new_tree_node

	def process_toe_tag(self, parent_element, element):
		if len(element.getAttribute('toe:if')) > 0:
			if not self.process_condition(element.getAttribute('toe:if')):
				return None

		if element.tagName.find('import'):
			return self.process_toe_import_tag(parent_element, element)

	def process_toe_import_tag(self, parent_element, element):
		file_name = element.getAttribute('file')

		imported_tree = {}

		if file_name.endswith(".html") or file_name.endswith(".htm"):
			with open(os.path.join(self.path_to_templates, file_name)) as f:			
					imported_tree = minidom.parseString(str(f.read()))
		if type(imported_tree) is xml.dom.minidom.Document:
			self.remove_blanks(imported_tree)
			imported_tree.normalize()
		
			top_node = self.new_tree.createElement(imported_tree.childNodes[0].childNodes[0].tagName)
			for child_node in imported_tree.childNodes[0].childNodes[0].childNodes:				
				new_node = self.process_subtree(top_node, child_node)
				top_node.appendChild(new_node)
			return top_node
		return None

	def process_if_attribute(self, parent_element, element):
		if not self.process_condition(element.getAttribute('toe:if')):
			return None
		element.removeAttribute('toe:if')
		return self.process_subtree(parent_element, element)

	def process_for_attribute(self, parent_element, element):
		result_nodes = []
		# get toe:for attribute
		iterable_cond = element.getAttribute('toe:for')
		# split string between " in "
		items = iterable_cond.split(" in ")
		# find variable on the right side
		# create python for loop
		iterable_item = self.current_scope.find_variable(items[1])
		if iterable_item is None:
			return None

		element.removeAttribute('toe:for')

		for thing in iterable_item:
		# local scope creation
			local_scope = Variable_Scope({}, self.current_scope)
			self.current_scope = local_scope

			self.current_scope.variables[items[0]] = thing

			# process subtree
			result_node = self.process_subtree(parent_element, element)
			if result_node is not None:
				result_nodes.append(result_node)

			# local scope destruction
			self.current_scope = self.current_scope.parent_scope
			local_scope = None
		return result_nodes

	def process_while_attribute(self, parent_element, element):
		result_nodes = []
		# get toe:for attribute
		iterable_cond = element.getAttribute('toe:while')
		
		if iterable_cond.find(" "):
			contains_condition = False
			for cond in (" gt ", " gte ", " lt ", " lte ", " eq ", " neq "):
				if cond in iterable_cond:
					contains_condition = True
			
			if not contains_condition:
				return None
		else:
			iterable_item = self.current_scope.find_variable(iterable_cond)
			if not isinstance(iterable_item, Iterable):
				return None

		# create python for loop
		if iterable_item is None:
			return None

		element.removeAttribute('toe:while')

		for thing in iterable_item:
		# local scope creation
			local_scope = Variable_Scope({}, self.current_scope)
			self.current_scope = local_scope

			self.current_scope.variables[items[0]] = thing

			# process subtree
			result_node = self.process_subtree(parent_element, element)
			if result_node is not None:
				result_nodes.append(result_node)

			# local scope destruction
			self.current_scope = self.current_scope.parent_scope
			local_scope = None
		return result_nodes

	def process_condition(self, condition):
		# Look at https://github.com/xgebi/SlothCMS-archive/blob/c4520ac6519de36a0ef5a42d0827e3b1f467504d/src/php/services/template/TemplateService.php#L251
		condition = condition.strip()
		if condition.find(" ") == -1:
			return self.current_scope.find_variable(condition)

		if condition.find(" gte "):
			pass
		if condition.find(" gt "):
			pass
		if condition.find(" lte "):
			pass
		if condition.find(" lt "):
			pass
		if condition.find(" neq "):
			pass
		if condition.find(" eq "):
			pass
		return False

	# Adapted from https://stackoverflow.com/a/16919069/6588356
	def remove_blanks(self, node):
		for x in node.childNodes:
			if x.nodeType == Node.TEXT_NODE:
				if x.nodeValue:
					x.nodeValue = x.nodeValue.strip()
			elif x.nodeType == Node.ELEMENT_NODE:
				self.remove_blanks(x)

class Variable_Scope:
	variables = {}
	parent_scope = None

	def __init__(self, variable_dict, parent_scope = None):
		self.variables = variable_dict
		self.parent_scope = parent_scope

	def find_variable(self, variable_name):
		if self.variables.get(variable_name) is not None:
			return self.variables.get(variable_name)
		
		if self.parent_scope is not None:
			return self.parent_scope.find_variable(variable_name)
		return None
	