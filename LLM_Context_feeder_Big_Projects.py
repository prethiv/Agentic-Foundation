import os


def build_context_file(root_dir, output_file="out.txt"):
    # Folders to strictly ignore
    ignore_dirs = {
        'node_modules', '.git', 'target', 'build', 'out','.idea',
        '.gradle', '.settings', 'bin', 'obj', 'dist', '__pycache__', '.idea', '.vscode'
    }

    # Extensions to include
    include_extensions = {
        '.kt', '.kts', '.swift', '.java', '.js', '.jsx',
        '.ts', '.tsx', '.py', '.html', '.css', '.json',
        '.xml', '.properties', '.yml', '.yaml', '.sql', '.md'
    }

    file_count = 0

    try:
        with open(output_file, "w", encoding="utf-8") as out:
            # os.walk is recursive by default
            for root, dirs, files in os.walk(root_dir):

                # Filter out ignored directories so os.walk doesn't even enter them
                dirs[:] = [d for d in dirs if d not in ignore_dirs]

                print(f"Scanning: {root}")  # Debug: See which folder we are in

                for file in files:
                    # Check if the file has a valid extension
                    if any(file.endswith(ext) for ext in include_extensions):
                        file_path = os.path.join(root, file)

                        try:
                            # Using errors="ignore" to skip binary data safely
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()

                            out.write(f'file path: "{file_path}"\n')
                            out.write("```\n")
                            out.write(content)
                            out.write("\n```\n\n")
                            file_count += 1

                        except Exception as e:
                            print(f"  [!] Could not read {file}: {e}")

        print(f"\n--- Process Complete ---")
        print(f"Total files written: {file_count}")
        print(f"Output saved to: {os.path.abspath(output_file)}")

    except Exception as e:
        print(f"Critical error: {e}")


if __name__ == "__main__":
    # Ensure this path is correct relative to where you run the script
    # Use "." if you are running the script INSIDE the project root
    project_path = "C:\\Users\\preth\\AndroidStudioProjects\\EvCompanion_MP"

    if os.path.exists(project_path):
        build_context_file(project_path)
    else:
        print(f"Error: The path '{project_path}' does not exist.")
