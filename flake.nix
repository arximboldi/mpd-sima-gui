{
  description = "GTK4/Adwaita GUI for mpd-sima";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        python = pkgs.python312;
        pythonPackages = python.pkgs;

        # Runtime dependencies for GObject introspection
        gtkDeps = [
          pkgs.gtk4
          pkgs.libadwaita
          pkgs.gobject-introspection
          pkgs.gdk-pixbuf
          pkgs.pango.out
          pkgs.glib.out
          pkgs.harfbuzz
          pkgs.cairo
          pkgs.graphene
          pkgs.librsvg
        ];

        giTypeLibPath = pkgs.lib.makeSearchPath "lib/girepository-1.0" gtkDeps;

        # Create a Python environment with the required packages
        pythonEnv = python.withPackages (ps: with ps; [
          pygobject3
          pycairo
        ]);

        sima-gui = pythonPackages.buildPythonApplication {
          pname = "sima-gui";
          version = "0.1.0";
          format = "pyproject";

          src = ./.;

          nativeBuildInputs = with pythonPackages; [
            setuptools
            wheel
          ] ++ [
            pkgs.gobject-introspection
            pkgs.wrapGAppsHook4
          ];

          buildInputs = gtkDeps;

          propagatedBuildInputs = with pythonPackages; [
            pygobject3
            pycairo
          ];

          # Don't wrap twice
          dontWrapGApps = true;

          postInstall = ''
            # Install icons
            mkdir -p $out/share/icons/hicolor/scalable/apps
            cp ${./logos}/*.svg $out/share/icons/hicolor/scalable/apps/
          '';

          preFixup = ''
            makeWrapperArgs+=("''${gappsWrapperArgs[@]}")
            makeWrapperArgs+=("--prefix" "PATH" ":" "${pkgs.lib.makeBinPath [ pkgs.mpd-sima pkgs.xdg-utils ]}")
            makeWrapperArgs+=("--prefix" "GI_TYPELIB_PATH" ":" "${giTypeLibPath}")
            makeWrapperArgs+=("--prefix" "XDG_DATA_DIRS" ":" "$out/share")
          '';

          meta = with pkgs.lib; {
            description = "GTK4/Adwaita GUI for mpd-sima";
            homepage = "https://github.com/example/sima-gui";
            license = licenses.gpl3Plus;
            maintainers = [];
            platforms = platforms.linux;
            mainProgram = "sima-gui";
          };
        };

      in {
        packages = {
          default = sima-gui;
          sima-gui = sima-gui;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pythonEnv

            # Runtime
            pkgs.mpd-sima
            pkgs.xdg-utils

            # Development tools
            pythonPackages.python-lsp-server
            pkgs.ruff
          ] ++ gtkDeps;

          shellHook = ''
            export GI_TYPELIB_PATH="${giTypeLibPath}"
            export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath gtkDeps}"
            echo "sima-gui development environment (GTK4/Adwaita)"
            echo "Run: python -m sima_gui"
          '';
        };

        apps.default = {
          type = "app";
          program = "${sima-gui}/bin/sima-gui";
        };
      }
    );
}
