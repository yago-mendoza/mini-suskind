import os
import cmd
import random
import argparse

import sktools as sk

from skplaceholder import *
from aux_clis import *

from visuals import *


# >> en sets 'en' as field (WRONG)


class SK_Interface (cmd.Cmd):
    
    def __init__(self, graph):

        super().__init__()
        self.G = graph 
        self.placeholder = Placeholder(self)
        self.response = None
        self.grabbed_nodes = []

        self.nodes_hist = []

        self._set_random_node()

        self.ls_default_lang = None
        self.ls_default_type = None

        self.r_default_lang = None
        self.r_default_type = None

    # Public Methods ----    

    def do_cd(self, arg):
        # Initializes an argument parser specifically for the 'cd' (change directory) command.
        parser = argparse.ArgumentParser()
        # Defines 'name' as a positional argument that can accept multiple values, representing the target node's name.
        parser.add_argument('name', nargs='*', help='The name to search for')

        try:
            # Parses the arguments from the input string. The 'split' method breaks it into a list of arguments.
            parsed_args = parser.parse_args(arg.split())
            # Combines the list of 'name' arguments back into a single string, representing the full name of the target node.
            parsed_name = ' '.join(parsed_args.name)

        except SystemExit:
            # Handles the situation where argparse encounters a parsing error and attempts to exit the script.
            # Intercepting SystemExit here prevents the entire CLI from shutting down due to a malformed command.
            padded_print("Invalid command or arguments. Type 'help cd' for more information.", tab=0)
            return
        
        if parsed_name == '..':
            if len(self.nodes_hist)>1:
                last_node = self.nodes_hist.pop(-1)
                if self.placeholder.node == last_node:
                    last_node = self.nodes_hist.pop(-1)
                self._set_node(last_node)
            else:
                print('Reached base state.')
        
        else:
            nodes = self.G.select(name=parsed_name)

            # Processes the search results based on the number of nodes found.
            if len(nodes) == 1:
                # If exactly one matching node is found, it's automatically set as the current context.
                self._set_node(nodes[0])

            else:
                
                # If multiple matching nodes are found, indicates a future feature for user selection.
                if nodes:
                    options = [node._convert_header_to_compact_format() for node in nodes]
                else:
                    number_of_guesses = 4
                    nodes = sk.find_similars(graph=self.G, target_name=parsed_name, k=number_of_guesses)
                    options = [node._convert_header_to_compact_format() for node in nodes]

                header_statement = "Do you mean ..."
                tail_statement = "(Press Enter without any input to exit)"

                SelectInterface(options, self, header_statement, tail_statement).cmdloop()
                response = self._get_response()
                if response:
                    if response.isdigit():
                        self._set_node(nodes[int(response)-1])
                    else:
                        padded_print('Could not identify index.')

    def do_r(self, args):
        parser = argparse.ArgumentParser(description="Perform a random node search")
        parser.add_argument('-l', '--lang', type=str, nargs='?', const='', default=None, help='Specify the language or reset')
        parser.add_argument('-t', '--type', type=str, nargs='?', const='', default=None, help='Specify the type or reset')
        parser.add_argument('-s', '--sos', type=str, default=None, help='Sets a bias for low-connected nodes.')
        parser.add_argument('-f', '--fav', action='store_true', help='Toggle favorite switch')
        try:
            args = parser.parse_args(args.split())
        except SystemExit:
            return 

        # Actualiza o elimina las restricciones globales basándose en los argumentos
        if args.lang is not None:
            if args.lang == '' and self.r_default_lang:
                print(f"([!] Succesfully unset `r` global filter '{self.r_default_lang}')")
                self.r_default_lang = None  # Elimina la restricción si el argumento es una cadena vacía
            elif args.lang != '':
                if args.lang != self.r_default_lang:
                    self.r_default_lang = args.lang  # Actualiza la restricción global
                    print(f"([!] Global filter set for `r` at '{self.r_default_lang}'; 'r -l' to unset)")

        if args.type is not None:
            if args.type == '' and self.r_default_type:
                print(f"([!] Succesfully unset `r` global filter '{self.r_default_type}')")
                self.r_default_type = None  # Elimina la restricción si el argumento es una cadena vacía
            elif args.type != '':
                if args.type != self.r_default_type:
                    self.r_default_type = args.type  # Actualiza la restricción global
                    print(f"([!] Global filter set for `r` at '{self.r_default_type}'; 'r -t' to unset)")

        # Aplica las restricciones globales para el filtrado
        lang_constraint = self.r_default_lang
        type_constraint = self.r_default_type

        if args.sos is not None:
            try:
                sos_value = int(args.sos)  # Try to convert args.sos to an integer
                candidates = self.G.edge_count('<=', sos_value)
            except ValueError:
                print("Error: 'sos' argument must be an integer.")
                return  # Exit the function or handle the error as appropriate
        else:
            candidates = self.G  # No 'sos' filter applied
    
        new_node = candidates.random(lang=lang_constraint, type=type_constraint, favorite=args.fav)

        if new_node:
            self._set_node(new_node)
        else:
            padded_print('No nodes met the criteria.', tab=0)

    def do_ls(self, arg):

        args = arg.split()

        if args and args[0] in ('y0', 'y1', 'y2', 'e0', 'e1', 'e2'):
            self.placeholder.fields = []
            self.placeholder.update_field('add', args.pop(0))

        parser = argparse.ArgumentParser(description='List information about the current node.')
        parser.add_argument('-d', '--details', action='store_true', default=None, help='Provides a more detailed display.')
        parser.add_argument('-w', '--width', type=int, default=35, help='Width for the column.')
        parser.add_argument('-a', '--abbr', type=int, default=None, help='Abbreviate all results to a maximum length.')
        parser.add_argument('-p', '--stop', type=int, default=None, help='Set a max of nodes to be displayed.')
        parser.add_argument('-c', '--ncol', type=int, default=4, help='Number of columns.')
        parser.add_argument('-r', '--shuffle', action='store_true', help='Shuffles the results.')

        parser.add_argument('-l', '--lang', nargs='?', const='', default=None, help='Filter by language and sets it as default for following "ls". No argument resets to default.')
        parser.add_argument('-t', '--type', nargs='?', const='', default=None, help='Filter by type and sets it as default for following "ls". No argument resets to default.')
        
        ls_args, unknown = parser.parse_known_args(args)
        
        if unknown:
            padded_print(f'Unrecognized argument(s): {" ".join(unknown)}', tab=0)

        if self.placeholder.fields:

            nodes = self.placeholder.node.get_neighbors(self.placeholder.fields)

            # Reset language filter if '-l' is used without an argument.
            if ls_args.lang == '':
                print(f"([!] Successfully unset `ls` global filter '{self.ls_default_lang}')")
                self.ls_default_lang = None
            elif ls_args.lang is not None:
                self.ls_default_lang = ls_args.lang

            if ls_args.type == '':
                self.ls_default_type = None
                print(f"([!] Successfully unset `ls` global filter '{self.ls_default_type}')")
            elif ls_args.type is not None:
                self.ls_default_type = ls_args.type
                
            if self.ls_default_lang:
                print(f"([!] Global filter set for `ls` at '{self.ls_default_lang}'; 'ls -l' to unset)")
                nodes = nodes.select(lang=self.ls_default_lang)
            if self.ls_default_type:
                print(f"([!] Global filter set for `ls` at '{self.ls_default_type}'; 'ls -t' to unset)")
                nodes = nodes.select(type=self.ls_default_type)

            nodes = sorted(nodes, key=lambda node: node.name)

            if nodes:

                if ls_args.shuffle:
                    random.shuffle(nodes)

                if ls_args.stop:
                    if ls_args.stop <= len(nodes):
                        nodes = nodes[:ls_args.stop]

                if ls_args.details:

                    # sin ponemos details, aplican todos los criterios menos 'abbr'
                    # solo tienen sentido 'stop' y 'r' de 'random/suffle'
                    to_print = []
                    max_index_length = len(str(len(nodes) - 1))  # Length of the largest index

                    for i, node in enumerate(nodes):
                        sizes = [str(i) for i in node.get_sizes()]
                        str_sizes = '/'.join(sizes[:3]) + ' - ' + '/'.join(sizes[3:])
                        to_print.append(f'[{node.lang}][{node.type}][{node.name}][{node.lemma}]....({str_sizes})')
                    for i, _ in enumerate(to_print):
                        print(f"{str(i+1).zfill(max_index_length)}) {_}")
                
                else:

                    names = [node.name for node in nodes]
                        
                    if ls_args.abbr:
                        names = [name[:ls_args.abbr] + '...' if len(name) > ls_args.abbr else name for name in names]

                    if len(self.placeholder.fields) == 1:
                        print(f"(SYS: Started edit-session at {datetime.datetime.now().strftime('%H:%M:%S')})")
                    
                    print(f"Showing {len(names)}/{len(self.placeholder.node.get_neighbors(self.placeholder.fields))} results.")
                    strings_to_display = [f'| {i+1}. {name}' for i, name in enumerate(names)]
                    
                    formatted_lines = get_n_columns_from_elements(strings_to_display, ncol=1, col_width=ls_args.width)
                    for line in formatted_lines:
                        print(line)
            else:
                padded_print('The set field for the target node is empty.', tab=0)

            if len(self.placeholder.fields) == 1 :
                LS_Interface(nodes, self, ls_args)

        if not self.placeholder.fields:
            padded_print("Error. Search field is needed", tab=0)

    # Internal Methods  --------------------
        
    def _set_node(self, new_node):
        if new_node:
            self.placeholder.update_node(new_node)
            if not self.nodes_hist or new_node != self.nodes_hist[-1]:
                self.nodes_hist.append(new_node)

    def _set_random_node(self, **kwargs):
        new_node = self.G.random(**kwargs)
        if new_node:
            self._set_node(new_node)
        else:
            padded_print('No nodes met the criteria.', tab=0)
    
    def _get_response(self, reset_response=True):
        # Gets and decides wether it resets the response or not (by default, it does)
        res, self.response = self.response, None if reset_response else self.response
        return res

    # CMD private re-writen methods --------------------
        
    def do_clear(self, arg):
        self.preloop()
        
    def preloop(self):
        os.system('cls')
        print('-'*47)

    def default(self, line):

        # Function to select a node from a list of matched nodes.
        def select_node(matched_nodes):
                
            header_statement = "Did you mean..."
            tail_statement = "(Press Enter to select none)"

            # Convert each node to a compact format suitable for display.
            formatted_nodes = [node._convert_header_to_compact_format() for node in matched_nodes]
            
            # Display the selection interface with formatted nodes and get user response.
            SelectInterface(formatted_nodes, self, header_statement, tail_statement).cmdloop()
            response = self._get_response()
            
            # Return the selected node based on user input or None if no selection was made.
            return matched_nodes[int(response)-1] if response else None
        
        # Function to bind a node to the current node with a specified edge type.
        def bind_node(current_node, selected_node, edge_type):
            # Check if the selected node is not already a neighbor with the specified edge type.
            if selected_node and not selected_node in current_node.get_neighbors(edge_type):
                # If not, bind the nodes together with the specified edge type.
                self.G.bind(current_node, selected_node, edge_type)
                print(f"| Successfully binded '{selected_node.name}'.")
            elif selected_node:
                # Inform if the node was already present and thus not added again.
                print('| The node was already present.')

        # Handling command line input for node manipulation.
        if (line.startswith('y') or line.startswith('e')) and len(line)==2:
            # Clear existing fields for placeholder if the line matches specific fields.
            self.placeholder.fields = []
            self.placeholder.update_field('add', line)
        elif (line.startswith('y') or line.startswith('e')) and len(line)==1:
            # Reset fields and expand command shorthand for further processing.
            self.placeholder.fields = []
            if line == 'e':
                line = ['e0', 'e1', 'e2']
            elif line == 'y':
                line = ['y0', 'y1', 'y2']
            for _ in line:
                self.placeholder.update_field('add', _)
        elif len(line)>2:
            if len(self.placeholder.fields)==1:
                # Attempt to match or create node based on extended input.
                matches = self.G.select(name=line)
                selected_node = None
                if matches:
                    # Handle multiple matches through selection or direct assignment.
                    if len(matches) > 1:
                        selected_node = select_node(matches)
                    else:
                        selected_node = matches[0]
                
                else:
                    # If no matches, prompt for node creation.
                    print('(SYS: Name does not match any node. Fill to create it.)')
                    lang =  input('> lang  : ').strip()
                    type =  input('> type  : ').strip()
                    lemma = 'NA' 
                    # Validate inputs for new node creation.
                    if lang and type and len(lang) == 2 and len(type) == 1:
                        # Check if a node with specified characteristics exists, create if not.
                        if not self.G.select(lang=lang, type=type, name=line, lemma=lemma):
                            self.G.create_node(lang, type, line, lemma)
                            print("| Node created.")
                            selected_node = self.G.select(lang=lang, type=type, name=line, lemma=lemma)[0]
                        else:
                            print('| The specified set of characteristics already exists.')
                    elif lang or type or lemma:
                        # Fail if any validation for the new node attributes fails.
                        print('Failed to validate hash attributes.')
                        
                # Binding or linking logic if a selected or created node is available.
                cn = self.placeholder.node
                cf = self.placeholder.fields[0]

                if selected_node:
                    if selected_node!=self.placeholder.node:
                        bind_node(cn, selected_node, cf)
                    else:
                        padded_print("Can't bind node to itself.")
            else:
                padded_print("Select a single valid fielding.")
        else:
            padded_print(f"Unknown '{line[:4].strip()+'...' if len(line)>5 else line}' command.", tab=0)
    
    def do_q(self, arg):
        return True
    
    def do_exit(self, arg):
        return True
