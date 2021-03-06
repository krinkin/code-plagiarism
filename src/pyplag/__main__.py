import context
import ast
import os
import sys
import numpy as np
import pandas as pd

from time import perf_counter
from src.pyplag.tfeatures import ASTFeatures
from src.pyplag.utils import get_AST, run_compare, print_compare_res
from src.github_helper.utils import get_list_of_repos, select_repos
from src.github_helper.utils import get_python_files_links, get_code
from src.github_helper.utils import get_github_api_link
from termcolor import colored

pd.options.display.float_format = '{:,.2%}'.format

# 0 mode works with GitHub repositoryes
# 1 mode works with directory in user computer

directory = 'py/'
if len(sys.argv) > 2:
    file_path = sys.argv[1]
    reg_exp = sys.argv[2]
    mode = 0
elif len(sys.argv) == 2:
    directory = sys.argv[1]
    mode = 1
    if not os.path.exists(directory):
        print('Directory isn\'t exist')
        exit()
elif len(sys.argv) == 1:
    exit()

tree1 = None
start_eval = perf_counter()
weights = np.array([1, 0.8, 0.8, 0.8], dtype=np.float32)
if mode == 0:
    if file_path.startswith('https://'):
        file_link = get_github_api_link(file_path)
        try:
            tree1 = ast.parse(get_code(file_link))
        except Exception as e:
            print('-' * 40)
            print(colored('Not compiled: ' + file_link, 'red'))
            print(colored(e.__class__.__name__, 'red'))
            for el in e.args:
                print(colored(el, 'red'))
            print('-' * 40)
            exit()
    else:
        tree1 = get_AST(file_path)

    if tree1 is None:
        exit()

    features1 = ASTFeatures()
    features1.visit(tree1)

    iteration = 0
    repos, repos_url = get_list_of_repos()
    repos, repos_url = select_repos(repos, repos_url, reg_exp)
    count_iter = len(repos)
    for repo_url in repos_url:
        print(repo_url)
        url_files_in_repo = get_python_files_links(repo_url + '/contents')
        inner_iter = 0
        inner_iters = len(url_files_in_repo)
        for url_file in url_files_in_repo:
            try:
                tree2 = ast.parse(get_code(url_file))
            except IndentationError as err:
                print('-' * 40)
                print(colored('Not compiled: ' + url_file, 'red'))
                print(colored('IdentationError: ' + err.args[0], 'red'))
                print(colored('In line ' + str(err.args[1][1]), 'red'))
                print('-' * 40)
                continue
            except SyntaxError as err:
                print('-' * 40)
                print(colored('Not compiled: ' + url_file, 'red'))
                print(colored('SyntaxError: ' + err.args[0], 'red'))
                print(colored('In line ' + str(err.args[1][1]), 'red'))
                print(colored('In column ' + str(err.args[1][2]), 'red'))
                print('-' * 40)
                continue
            except TabError as err:
                print('-' * 40)
                print(colored('Not compiled: ' + url_file, 'red'))
                print(colored('TabError: ' + err.args[0], 'red'))
                print(colored('In line ' + str(err.args[1][1]), 'red'))
                print('-' * 40)
                continue
            except Exception as e:
                print('-' * 40)
                print(colored('Not compiled: ' + url_file, 'red'))
                print(colored(e.__class__.__name__, 'red'))
                for el in e.args:
                    print(colored(el, 'red'))
                print('-' * 40)
                continue

            features2 = ASTFeatures()
            features2.visit(tree2)
            metrics = run_compare(features1, features2)
            total_similarity = np.sum(metrics * weights) / 4

            if total_similarity > 0.7:
                print_compare_res(metrics, total_similarity,
                                  features1.structure,
                                  features2.structure,
                                  features1.from_num,
                                  features2.from_num,
                                  features1.seq_ops,
                                  features2.seq_ops,
                                  features1.tokens,
                                  features2.tokens,
                                  file_path.split('\\')[-1],
                                  url_file)

            inner_iter += 1
            print('In repo {:.2%}, In repos {:.2%}'.format((inner_iter /
                                                            inner_iters),
                                                           (iteration /
                                                            count_iter)),
                  end="\r")
        iteration += 1
        print(repo_url, " ... OK")
        print(" " * 40, end="\r")
        print('In repos {:.2%}'.format(iteration / count_iter), end="\r")
elif mode == 1:
    files = os.listdir(directory)
    files = list(filter(lambda x: (x.endswith('.py')), files))

    count_files = len(files)
    # date = datetime.datetime.now().strftime('%Y%m%d-%H#%M#%S')
    # log_file = open('./logs/pylog' + date + '.txt', 'w')

    iterrations = (count_files * count_files - count_files) / 2
    iterration = 0

    for row in np.arange(0, count_files, 1):
        if directory[-1] != '/':
            directory += '/'
        filename = directory + files[row]
        for col in np.arange(0, count_files, 1):
            filename2 = directory + files[col]
            if row == col:
                continue
            if row > col:
                continue

            tree1 = get_AST(filename)
            tree2 = get_AST(filename2)

            if tree1 is None:
                break
            if tree2 is None:
                continue

            features1 = ASTFeatures()
            features2 = ASTFeatures()
            features1.visit(tree1)
            features2.visit(tree2)

            metrics = run_compare(features1, features2)
            total_similarity = np.sum(metrics * weights) / weights.sum()

            if total_similarity > 0.7:
                print_compare_res(metrics, total_similarity,
                                  features1.structure,
                                  features2.structure,
                                  features1.from_num,
                                  features2.from_num,
                                  features1.seq_ops,
                                  features2.seq_ops,
                                  features1.tokens,
                                  features2.tokens,
                                  filename.split('/')[-1],
                                  filename2.split('/')[-1])

            iterration += 1
            print('  {:.2%}'.format(iterration / iterrations), end="\r")

    if count_files == 0:
        print("Folder is empty")

print("Analysis complete")
print('Time for all {:.2f}'.format(perf_counter() - start_eval))
# log_file.close()
