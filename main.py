if __name__ == '__main__':
    import os
    from skgraph import Graph
    from SKCLI import *
    data_file_path = os.path.normpath('data.txt')
    G = Graph(data_file_path)
    SK_Interface(G).cmdloop()
