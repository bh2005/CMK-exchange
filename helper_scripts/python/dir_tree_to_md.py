import os
import argparse

def generate_tree(start_path, prefix=''):
    """
    Generates an ASCII directory tree string from a given path.
    """
    tree_lines = []
    
    # Get all entries (files and directories) and sort them
    contents = sorted(os.listdir(start_path))
    
    # Iterate through each entry to build the tree structure
    for i, item in enumerate(contents):
        path = os.path.join(start_path, item)
        is_last = (i == len(contents) - 1)
        
        # Determine the correct ASCII characters for the tree structure
        if is_last:
            tree_lines.append(f"{prefix}└── {item}")
            new_prefix = f"{prefix}    "
        else:
            tree_lines.append(f"{prefix}├── {item}")
            new_prefix = f"{prefix}│   "
            
        # Recursively call the function if the item is a directory
        if os.path.isdir(path):
            tree_lines.extend(generate_tree(path, new_prefix))
            
    return tree_lines

def main():
    """
    Main function to parse command-line arguments and run the script.
    """
    parser = argparse.ArgumentParser(description="Generate an ASCII directory tree and save it as a Markdown file.")
    parser.add_argument('directory', type=str, help="The path to the directory to be scanned.")
    parser.add_argument('--output', type=str, default='directory_tree.md', help="The name of the output Markdown file.")
    
    args = parser.parse_args()
    
    target_dir = args.directory
    output_file = args.output
    
    if not os.path.isdir(target_dir):
        print(f"Error: The directory '{target_dir}' does not exist.")
        return
        
    print(f"Generating directory tree for '{target_dir}'...")
    tree_lines = generate_tree(target_dir)
    
    # Prepare the Markdown content
    md_content = f"# Directory Tree for '{target_dir}'\n\n"
    md_content += "```\n"
    md_content += f"{os.path.basename(target_dir)}\n"
    md_content += "\n".join(tree_lines)
    md_content += "\n```\n"
    
    # Write the content to the Markdown file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print(f"Successfully saved the tree to '{output_file}'.")

if __name__ == "__main__":
    main()