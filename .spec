from PyInstaller.utils.hooks import collect_submodules

# This recursively finds every .py file in 'src' and tells 
# PyInstaller: "Trust me, I'm going to import these later."
hidden_src_modules = collect_submodules('src')

a = Analysis(
    ['main.py'],
    hiddenimports=hidden_src_modules
)