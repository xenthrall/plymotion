"""Plymotion CLI - Convert videos to Plymouth boot splash animations."""

from __future__ import annotations

from pathlib import Path

import typer

from plymotion import __version__

app = typer.Typer(
    name="plymotion",
    help="Convert videos into Plymouth boot splash animations.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"plymotion {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Plymotion - Video to Plymouth boot splash converter."""


@app.command()
def convert(
    video_input: Path = typer.Option(
        ..., "--video-input", "-i",
        exists=True,
        readable=True,
        help="Path to input video file (mp4, webm, avi).",
    ),
    output_dir: Path = typer.Option(
        Path("./plymotion-output"), "--output-dir", "-o",
        help="Output directory for generated theme.",
    ),
    resolution: str = typer.Option(
        "1920x1080", "--resolution", "-r",
        help="Target resolution as WxH (e.g. 1920x1080).",
    ),
    fps: int = typer.Option(
        30, "--fps", "-f",
        help="Frames per second to extract.",
    ),
    theme_name: str = typer.Option(
        "plymotion", "--theme-name", "-t",
        help="Name for the generated Plymouth theme.",
    ),
    image_dir: str | None = typer.Option(
        None,
        "--image-dir",
        help="ImageDir path written into generated theme files "
             "(default: /usr/share/plymouth/themes/<theme-name>).",
    ),
    install: bool = typer.Option(
        False, "--install",
        help="Install the generated theme system-wide after conversion (requires sudo).",
    ),
) -> None:
    """Convert a video to a Plymouth boot splash theme."""
    from plymotion.frame_processor import optimize_frames
    from plymotion.template_generator import generate_plymouth, generate_script
    from plymotion.video_extractor import extract_frames

    # Parse resolution
    try:
        w, h = resolution.lower().split("x")
        target_w, target_h = int(w), int(h)
    except ValueError:
        typer.echo(f"Invalid resolution: {resolution}. Use WxH format.", err=True)
        raise typer.Exit(1)

    resolved_image_dir = image_dir or f"/usr/share/plymouth/themes/{theme_name}"

    # Info
    typer.echo(f"Plymotion v{__version__}")
    typer.echo(f"Input:  {video_input}")
    typer.echo(f"Output: {output_dir}")
    typer.echo(f"Resolution: {target_w}x{target_h} @ {fps} fps")
    typer.echo()

    # Step 1: Extract frames directly into the theme dir (flat layout:
    # frames sit next to the .script/.plymouth files, matching ImageDir).
    typer.echo("Extracting frames with ffmpeg...")
    frame_count = extract_frames(video_input, output_dir, fps=fps)
    typer.echo(f"  Extracted {frame_count} frames.")

    # Step 2: Optimize frames
    typer.echo("Optimizing frames...")
    optimize_frames(output_dir, (target_w, target_h))
    typer.echo(f"  Optimized {frame_count} frames to {target_w}x{target_h}.")

    # Step 3: Generate theme files
    typer.echo("Generating Plymouth theme files...")
    script_path = output_dir / f"{theme_name}-plymouth.script"
    plymouth_path = output_dir / f"{theme_name}-plymouth.plymouth"

    generate_script(script_path, frame_count, resolved_image_dir)
    generate_plymouth(plymouth_path, theme_name, resolved_image_dir,
                      f"{resolved_image_dir}/{theme_name}-plymouth.script")
    typer.echo(f"  {script_path.name}")
    typer.echo(f"  {plymouth_path.name}")

    # Step 4: Install (optional) or print manual steps
    if install:
        from plymotion.installer import install_theme

        typer.echo()
        typer.echo("Installing theme (requires sudo)...")
        install_theme(output_dir, theme_name=theme_name)
        typer.echo("Installed! Reboot to see the new boot splash.")
    else:
        typer.echo()
        typer.echo("To install now, re-run with --install, or do it manually:")
        typer.echo(f"  sudo mkdir -p /usr/share/plymouth/themes/{theme_name}")
        typer.echo(f"  sudo cp {output_dir}/* /usr/share/plymouth/themes/{theme_name}/")
        typer.echo(
            f"  sudo update-alternatives --install "
            f"/usr/share/plymouth/themes/default.plymouth default.plymouth "
            f"/usr/share/plymouth/themes/{theme_name}/{theme_name}-plymouth.plymouth 120"
        )
        typer.echo("  sudo update-initramfs -u")

    typer.echo()
    typer.echo("Done!")


@app.command()
def gui() -> None:
    """Launch the graphical interface."""
    from plymotion.ui.app import run as run_gui

    run_gui()
