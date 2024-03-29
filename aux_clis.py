import cmd 
import datetime

from itertools import combinations

from visuals import *

import sktools as sk

class LS_Interface(cmd.Cmd):

    prompt = '>> '
    def __init__(self, listed_nodes, parent_cli, ls_args):
        super().__init__()
        self.ls_node = parent_cli.placeholder.node
        self.listed_nodes = listed_nodes
        self.parent_cli = parent_cli
        self.ls_args = ls_args
        self.response = None
        self.cmdloop()
    
    def do_cd(self, index): # finisehd
        if index.isdigit():
            new_current_node = self.listed_nodes[int(index)-1]
            self.parent_cli._set_node(new_current_node)
            return True
        else:
            print('Index must be digit.')
    
    def do_ls(self, arg=None):

        if arg:
            print("(SYS: arguments for 'ls' are disabled within the edit session)")
        self._update_listed_nodes()
        if not self.listed_nodes:
            print("The set field for the target node is empty.")
        strings_to_display = [f'| {i + 1}. {name}' for i, name in enumerate([node.name for node in self.listed_nodes])]

        if len(self.listed_nodes):
            print(f"Showing {len(self.listed_nodes)}/{len(self.listed_nodes)} results.")

        formatted_lines = get_n_columns_from_elements(strings_to_display, ncol=1, col_width=self.ls_args.width)
        for line in formatted_lines:
            print(line)

    def do_clear(self, arg):

        field_symb = self.parent_cli.placeholder.fields[0]
        field = ('synset' if field_symb[0] == 'y' else 'semset') + field_symb[1]

        ch = input(f'SYS: Are you sure you want to clear this field? [Y/N]\n>> ')
        if ch in {'Y','y'}:
            for node in self.listed_nodes:
                self.parent_cli.G.unbind(self.ls_node, node, field)
            print('Field succesfully cleared.')
            return True
        else:
            print('Cleansing process aborted.')
            

    def do_del(self, idxs):

        # revisar que tire

        idxs = sk.parse_idxs_to_single_idxs(idxs) # accepts ranges as 5-8 (5,6,7,8)
        unbind_cases = []
        for idx in idxs:
            target_node = self.listed_nodes[idx-1]
            field_symb = self.parent_cli.placeholder.fields[0]
            field = ('synset' if field_symb[0] == 'y' else 'semset') + field_symb[1]
            unbind_cases.append((target_node, field))
        for unbind_case in unbind_cases:
            self.parent_cli.G.unbind(self.ls_node, unbind_case[0], unbind_case[1])
        padded_print(f"Deleted {len(idxs)} nodes.")

        self.do_ls()
    
    def do_grab(self, idxs):
        idxs = sk.parse_idxs_to_single_idxs(idxs) # accepts ranges as 5-8 (5,6,7,8)
        if not idxs:
            idxs = list(range(len(self.listed_nodes)))
        for idx in idxs:
            target_node = self.listed_nodes[idx-1]
            if target_node not in self.parent_cli.grabbed_nodes:
                self.parent_cli.grabbed_nodes.append(target_node)

        padded_print(f'Grabbed {len(idxs)} nodes.')
    
    def do_cross(self, args):
        # Divide los argumentos en índices y tipo de relación
        parts = args.split()
        idxs = ' '.join(parts[:-1])  # Todos menos el último
        relation_type = parts[-1]  # Último argumento

        # Verifica si el tipo de relación es válido
        if relation_type not in ['y', 'e']:
            print("Invalid relation type. Use 'y' or 'e'.")
            return

        # Utiliza la función existente para convertir rangos en índices individuales
        idxs = sk.parse_idxs_to_single_idxs(idxs)

        selected_nodes = [self.listed_nodes[idx - 1] for idx in idxs] if idxs else self.listed_nodes

        # Bindea los nodos seleccionados
        for node1, node2 in combinations(selected_nodes, 2):
            # Bindea cada par de nodos
            self.parent_cli.G.bind(node1, node2, relation_type + '1')

        n_conn = len(selected_nodes)

        print(f"Nodes successfully binded ({int((n_conn*(n_conn-1))/2)} conn.) through '{relation_type + '1'}' field.")

    def default(self, line):

        line = line.strip()
        if line[0] in {'y', 'e'} and line[1] in {'0', '1', '2'} and len(line)==2:
            self.parent_cli.placeholder.fields = []
            self.parent_cli.placeholder.update_field('add', line)
            self.do_ls()
        
        elif len(line)>2:

            name = line       

            def capitalize_name(name):
                return name[0].upper() + name[1:] if name else None

            def select_node(matched_nodes):
                
                header_statement = "Did you mean..."
                tail_statement = "(Press Enter to select none)"
                formatted_nodes = [node._convert_header_to_compact_format() for node in matched_nodes]
                SelectInterface(formatted_nodes, self, header_statement, tail_statement).cmdloop()
                response = self._get_response()
                return matched_nodes[int(response)-1] if response else None

            def create_node():
                user_input = input("| Do you want to create this node? [Y/N] : ").strip().lower()

                if user_input in ['Y','y']:

                    lang =  input('> lang  : ').strip()
                    type =  input('> type  : ').strip()
                    lemma = 'NA'

                    return lang, type, lemma

                return None, None, None

            def bind_node(current_node, selected_node, edge_type):
                if selected_node and not selected_node in current_node.get_neighbors(edge_type):
                    self.parent_cli.G.bind(current_node, selected_node, edge_type)
                    print(f"| Successfully binded '{selected_node.name}'.")
                elif selected_node:
                    print('| The node was already present.')

            name = capitalize_name(name)

            matched_nodes = self.parent_cli.G.select(name=name)

            if matched_nodes:

                if len(matched_nodes) > 1:
                    selected_node = select_node(matched_nodes)
                else:
                    selected_node = matched_nodes[0]
            
            if not matched_nodes:

                selected_node = None

            if not selected_node:
                lang, type, lemma = create_node()
                if lang and type and len(lang) == 2 and len(type) == 1:
                    if not self.parent_cli.G.select(lang=lang, type=type, name=name, lemma=lemma):
                        self.parent_cli.G.create_node(lang, type, name, lemma)
                        selected_node = self.parent_cli.G.select(lang=lang, type=type, name=name, lemma=lemma)[0]
                        print("| Node created.")
                    else:
                        print('| The specified set of characteristics already exists.')
                elif lang or type or lemma:
                    print('Failed to validate hash attributes.')

            if selected_node:
                bind_node(self.ls_node, selected_node, self.parent_cli.placeholder.fields[0])
        
        else:
            padded_print(f"Unknown '{line[:4].strip()+'...' if len(line)>5 else line}' command.")

    def do_mv(self, arg):

        args = arg.split()
        fields = [arg for arg in args if arg in ['y0', 'y1', 'y2', 'e0', 'e1', 'e2']]
        idxs = [arg for arg in args if set(arg).issubset(set('0123456789-')) and arg not in fields]
        name = ' '.join([arg for arg in args if arg not in idxs and arg not in fields])
        
        numbers_set = set()
        for part in idxs:
            numbers_set.update(range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1)) if '-' in part else numbers_set.add(int(part))
        idxs = sorted(numbers_set)

        target_nodes = [self.listed_nodes[i-1] for i in idxs] if idxs else self.listed_nodes

        if name:
            homologous = self.parent_cli.G.select(name=name)
            if len(homologous) == 1:
                node = homologous[0]
            else:
                SelectInterface([node._convert_header_to_compact_format() for node in homologous], 
                            self, f"Found {len(homologous)} homologous.",
                            "(Select the node to operate)", '>> ').cmdloop()
                response = self._get_response()
                node = homologous[int(response)-1] if response.isdigit() else None
            if node:
                if not fields:
                    fields = self.parent_cli.placeholder.fields

                for field in fields:
                    for target_node in target_nodes:
                        self.parent_cli.G.bind(node, target_node, field)
                        self.parent_cli.G.unbind(self.ls_node, target_node, self.parent_cli.placeholder.fields[0])
                print(f'Succesfully re-binded {len(target_nodes)} edges.')
            else:
                print('Aborted process.')
        else:
            node = self.ls_node
            if fields:
                for field in fields:
                    for target_node in target_nodes:
                        self.parent_cli.G.bind(node, target_node, field)
                        self.parent_cli.G.unbind(node, target_node, self.parent_cli.placeholder.fields[0])
                print(f'Succesfully re-binded {len(target_nodes)} edges.')
            else:
                print('Not enough arguments provided.')

        self.do_ls()
    
    def do_cp(self, arg):

        args = arg.split()
        fields = [arg for arg in args if arg in ['y0', 'y1', 'y2', 'e0', 'e1', 'e2']]
        idxs = [arg for arg in args if set(arg).issubset(set('0123456789-')) and arg not in fields]
        name = ' '.join([arg for arg in args if arg not in idxs and arg not in fields])
        
        numbers_set = set()
        for part in idxs:
            numbers_set.update(range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1)) if '-' in part else numbers_set.add(int(part))
        idxs = sorted(numbers_set)

        target_nodes = [self.listed_nodes[i-1] for i in idxs] if idxs else self.listed_nodes

        if name:
            homologous = self.parent_cli.G.select(name=name)
            if len(homologous) == 1:
                node = homologous[0]
            else:
                SelectInterface([node._convert_header_to_compact_format() for node in homologous], 
                            self, f"Found {len(homologous)} homologous.",
                            "(Select the node to operate)", '>> ').cmdloop()
                response = self._get_response()
                node = homologous[int(response)-1] if response.isdigit() else None
            if node:
                if not fields:
                    fields = self.parent_cli.placeholder.fields

                for field in fields:
                    for target_node in target_nodes:
                        self.parent_cli.G.bind(node, target_node, field)
                print(f'Succesfully binded {len(target_nodes)} edges.')

            else:
                print('Aborted process.')
        else:
            if fields:

                for field in fields:
                    for target_node in target_nodes:
                        self.parent_cli.G.bind(self.ls_node, target_node, field)
                print(f'Succesfully binded {len(target_nodes)} edges.')
            else:
                print('Not enough arguments provided.')

        self.do_ls()
    
    def do_align(self, arg):
        args = arg.split()

        fields = [arg for arg in args if arg in ['y0', 'y1', 'y2', 'e0', 'e1', 'e2','e','y']]
        if fields:
            fields = sk.parse_field(fields)
        else:
            fields = sk.parse_field()

        idxs = [arg for arg in args if set(arg).issubset(set('0123456789-')) and arg not in fields]
        
        numbers_set = set()
        for part in idxs:
            numbers_set.update(range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1)) if '-' in part else numbers_set.add(int(part))
        idxs = sorted(numbers_set)

        # Determine the target nodes based on the specified indices
        target_nodes = [self.listed_nodes[i-1] for i in idxs] if idxs else self.listed_nodes

        if len(target_nodes)==1:
            # If we selected only one idx, we will align the current placeholder node with it.
            # We place it here to be able to collect also the connections of it.
            target_nodes.append(self.parent_cli.placeholder.node)

        # Initialize a dictionary to hold neighbors for each field
        d = {field: [] for field in fields}

        # Collect neighbors for each field from each target node
        for node in target_nodes:
            for field in fields:
                d[field].extend(node.get_neighbors(field))

        # Ensure all nodes in each field share the same bindings
        labels, contents = [], []
        for node in target_nodes:
            n_conn_o = len(node._get_raw_content())
            for field, neighbors in d.items():
                for neighbor in neighbors:
                    # Bind the target node to each neighbor in the current field
                    self.parent_cli.G.bind(node, neighbor, field)
            n_conn_f = len(node._get_raw_content())
            diff = n_conn_f-n_conn_o

            labels.append(node._convert_header_to_compact_format())
            contents.append(f"{n_conn_o} + {diff} conn. (+{round(100*diff/n_conn_o,2)}%)")

        formatted_lines = get_label_aligned_lines(labels, ' : ', contents)
        for line in formatted_lines:
            padded_print(line)

    def emptyline(self): #finished
        # To exit with an empty Enter key press
        print(f"(SYS: Ended edit-session at {datetime.datetime.now().strftime('%H:%M:%S')})")
        return True

    def cmdloop(self, intro=None):
        super().cmdloop(intro)

    def _get_response(self, reset_response=True):
        # Gets and decides wether it resets the response or not (by default, it does)
        res, self.response = self.response, None if reset_response else self.response
        return res

    def _update_listed_nodes(self):
        self.listed_nodes = list(self.ls_node.get_neighbors(self.parent_cli.placeholder.fields))
        # We update internal object self.listed_nodes to reflect changes that might have been made during the session
        self.listed_nodes = sorted(self.listed_nodes, key=lambda node: node.name)
        # We sort these nodes for readibility (by name)    
# POPUP CLIs ----------------------
    
    # These CLIs don't require HELP of any kind.
    
class SelectInterface(cmd.Cmd):

    def __init__(self, options, parent_cli, header_statement="", tail_statement="", prompt='>> '):
        super().__init__()
        self.options = options
        self.header_statement = header_statement
        self.tail_statement = tail_statement
        self.parent_cli = parent_cli
        self.prompt = prompt
        self.display()
    
    def display(self):
        padded_print(self.header_statement)
        for index, option in enumerate(self.options, start=1):
            string_index = str(index).zfill(2 if len(self.options)>10 else 1)
            padded_print(f"{string_index}) {option}", tab=1)
        padded_print(self.tail_statement)

    def deliver_result(self, response):
        self.parent_cli.response = None
        self.parent_cli.response = response

    def default(self, line):
        """
        The default method in a cmd.Cmd subclass is called when a command is entered
        that doesn't match any existing do_*
        """
        try:
            if isinstance(line, str) and not line.isdigit():
                self.deliver_result(line.strip())
            else:
                index = int(line) - 1  # Convert to zero-based index.
                if 0 <= index < len(self.options):
                    self.deliver_result(line)
                else:
                    print("Please enter a valid index.")
        except ValueError:
            print("Please enter a number to select an option or just press Enter to exit.")
        return True # exits loops
    
    def emptyline(self):
        # To exit with an empty Enter key press
        return True
    
    def do_exit(self, arg):
        return True 