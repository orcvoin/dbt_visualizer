# PYTHON script
## install graphviz


#### linux
`sudo apt install graphviz`
or
`sudo dnf install graphviz`

#### mac
`sudo port install graphviz`
or
`brew install graphviz`

#### windows

download installer from https://graphviz.org/download/

## install drawio desktop


#### linux
download and install "deb", "AppImage" or "rpm" from https://github.com/jgraph/drawio-desktop/releases
create symlink

`chmod +x /path/to/drawio.AppImage`

`mkdir -p ~/Applications`

`mv /path/to/drawio.AppImage ~/Applications/`

use name "drawio" for symlink
`ln -s ~/Applications/drawio.AppImage ~/bin/drawio`

#### mac
download and install "macOS - Universal" from https://github.com/jgraph/drawio-desktop/releases

#### windows
download installer from https://github.com/jgraph/drawio-desktop/releases

### REQUIREMENTS
`pip install -r requirements.txt`

# HOW TO USE:

`python3 generate_scheme.py --path /path_to/project_name/target/manifest.json --name project_name.xml`

# DOCKER:

1) build

2) `sudo docker build -t dbt-drawio .`

2) run

3) `sudo docker run -it -e MANIFEST_PATH=/data/manifest.json -v /absolute_path_to/project_folder/target/manifest.json:/data/manifest.json -p 6080:6080 dbt-drawio`

4) open `http://localhost:6080/vnc_auto.html` in browser and click "connect"