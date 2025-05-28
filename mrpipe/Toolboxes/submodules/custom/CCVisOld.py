import os
import numpy as np
import nibabel as nib
from skimage.measure import label, regionprops
from skimage import measure
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider
from mpl_toolkits.mplot3d import Axes3D
import argparse
import math
import threading
import time


def load_nifti(file_path):
    """Load a NIFTI file and return its data and affine transform."""
    img = nib.load(file_path)
    return img.get_fdata(), img.affine, img.header


def compute_eigenvectors_from_inertia(inertia_tensor):
    """Compute eigenvectors and eigenvalues from inertia tensor."""
    eigenvalues, eigenvectors = np.linalg.eigh(inertia_tensor)

    # Sort eigenvalues and eigenvectors in descending order
    idx = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    return eigenvalues, eigenvectors


class CCViewer:
    def __init__(self, cc_mask_file, scale_factor=1.0, colormap='viridis', alpha=0.3, mesh_simplify=0.2,
                 use_global_limits=False, margin_factor=2.5, debug=False, interior_mesh=True):
        # Enable debug mode if needed
        self.debug = debug
        self.interior_mesh = interior_mesh

        # Load data
        self.cc_data, self.cc_affine, _ = load_nifti(cc_mask_file)
        self.voxel_dims = np.array([np.sqrt(np.sum(self.cc_affine[:3, i] ** 2)) for i in range(3)])

        if self.debug:
            print(f"Voxel dimensions: {self.voxel_dims}")
            print(f"Affine matrix: \n{self.cc_affine}")

        # Label connected components
        self.cc_binary = self.cc_data > 0
        self.labeled_components, self.num_components = label(self.cc_binary, return_num=True)
        print(f"Found {self.num_components} connected components")

        # Store parameters
        self.scale_factor = scale_factor
        self.colormap = colormap
        self.cm = plt.get_cmap(colormap)
        self.alpha = alpha
        self.mesh_simplify = mesh_simplify
        self.use_global_limits = use_global_limits
        self.margin_factor = margin_factor

        # Initialize component index
        self.current_cc_idx = 1 if self.num_components > 0 else 0

        # Initialize component info dictionary
        self.component_info = {}
        self.background_thread = None
        self.processing_complete = False
        self.global_limits = None

        # Set up the figure and UI elements
        self.setup_figure()

        # Process the first component immediately
        if self.num_components > 0:
            self.component_info[1] = self.process_component(1)

            # Set initial local limits
            if not self.component_info[1].get("empty", True) and "mesh_info" in self.component_info[1]:
                mesh_info = self.component_info[1]["mesh_info"]
                # Create temporary global limits based on first component
                self.global_limits = []
                for dim in range(3):
                    center = mesh_info["center"][dim]
                    half_extent = mesh_info["extent"][dim] * self.margin_factor / 2
                    self.global_limits.append((center - half_extent, center + half_extent))

            # Start background thread to process the rest
            self.start_background_processing()

        # Draw initial component
        self.draw_component()

    def setup_figure(self):
        # Create main figure
        self.fig = plt.figure(figsize=(14, 10))

        # Main 3D axes for the component
        self.ax = self.fig.add_axes([0.1, 0.2, 0.8, 0.7], projection='3d')

        # Button axes
        self.prev_button_ax = self.fig.add_axes([0.25, 0.05, 0.1, 0.05])
        self.next_button_ax = self.fig.add_axes([0.65, 0.05, 0.1, 0.05])

        # CC selection slider
        self.slider_ax = self.fig.add_axes([0.4, 0.05, 0.2, 0.05])

        # Option for global vs local limits
        self.limits_button_ax = self.fig.add_axes([0.8, 0.05, 0.15, 0.05])

        # Status indicator
        self.status_ax = self.fig.add_axes([0.05, 0.05, 0.15, 0.05])
        self.status_text = self.status_ax.text(0.5, 0.5, "Processing...",
                                               ha='center', va='center')
        self.status_ax.axis('off')

        # Create buttons
        self.prev_button = Button(self.prev_button_ax, 'Previous')
        self.next_button = Button(self.next_button_ax, 'Next')
        self.limits_button = Button(self.limits_button_ax,
                                    'Global Limits' if self.use_global_limits else 'Local Limits')

        # Create slider
        self.slider = Slider(
            self.slider_ax, 'CC',
            1, self.num_components,
            valinit=self.current_cc_idx,
            valstep=1
        )

        # Connect callbacks
        self.prev_button.on_clicked(self.prev_component)
        self.next_button.on_clicked(self.next_component)
        self.slider.on_changed(self.slider_update)
        self.limits_button.on_clicked(self.toggle_limits)

        # Set up timer for checking background thread
        self.timer = self.fig.canvas.new_timer(interval=500)  # 500ms
        self.timer.add_callback(self.check_background_thread)
        self.timer.start()

    def check_background_thread(self):
        """Check if background processing is complete and update status."""
        if self.background_thread is not None and not self.background_thread.is_alive():
            if not self.processing_complete:
                self.processing_complete = True
                self.status_text.set_text("Processing complete")
                self.calculate_global_limits()
                if self.use_global_limits:
                    self.draw_component()  # Redraw with final global limits

        # If thread is still running, update status text with progress
        elif self.background_thread is not None:
            progress = len(self.component_info) / self.num_components * 100
            self.status_text.set_text(f"Processing... {progress:.1f}%")

    def toggle_limits(self, event):
        self.use_global_limits = not self.use_global_limits
        self.limits_button.label.set_text('Global Limits' if self.use_global_limits else 'Local Limits')
        self.draw_component()

    def start_background_processing(self):
        """Start background processing of remaining components."""
        self.background_thread = threading.Thread(target=self.process_remaining_components)
        self.background_thread.daemon = True  # Thread will exit when main program exits
        self.background_thread.start()

    def process_remaining_components(self):
        """Process all components except the first one (which was processed immediately)."""
        try:
            # Process components 2 and onwards
            for component_idx in range(2, self.num_components + 1):
                self.component_info[component_idx] = self.process_component(component_idx)
                # Brief sleep to allow UI to remain responsive
                time.sleep(0.01)

            # Calculate global limits once all components are processed
            self.calculate_global_limits()

            # Mark processing as complete
            self.processing_complete = True

        except Exception as e:
            print(f"Error in background processing: {str(e)}")

    def process_component(self, component_idx):
        """Process a single component and return its information."""
        # Extract this component
        component_mask = (self.labeled_components == component_idx)

        # Skip if component is empty
        if not np.any(component_mask):
            return {"empty": True}

        # Get component coordinates in voxel space
        voxel_coords = np.array(np.where(component_mask)).T  # [z, y, x]

        # Skip if no coordinates
        if len(voxel_coords) == 0:
            return {"empty": True}

        # Convert to real-world coordinates
        real_coords = voxel_coords * self.voxel_dims

        # Calculate bounds and center
        min_voxel = np.min(voxel_coords, axis=0)
        max_voxel = np.max(voxel_coords, axis=0)
        min_real = np.min(real_coords, axis=0)
        max_real = np.max(real_coords, axis=0)
        centroid_voxel = np.mean(voxel_coords, axis=0)
        centroid_real = np.mean(real_coords, axis=0)
        extent = max_real - min_real

        # Pre-compute marching cubes mesh
        # Create a padded version of the mask to ensure closed surfaces
        padded_shape = np.array(component_mask.shape) + 2
        padded_mask = np.zeros(padded_shape, dtype=np.int8)
        slices = tuple(slice(1, s + 1) for s in component_mask.shape)
        padded_mask[slices][component_mask] = 1

        try:
            try:
                # Try with default arguments
                verts, faces, normals, values = measure.marching_cubes(
                    padded_mask, level=0.5, spacing=self.voxel_dims,
                    allow_degenerate=False, step_size=1
                )
            except TypeError:
                # For older versions of scikit-image
                verts, faces = measure.marching_cubes_classic(
                    padded_mask, level=0.5, spacing=self.voxel_dims
                )

            # Adjust vertices to real-world coordinates
            # verts already includes voxel_dims scaling from spacing parameter
            # But starts at (0,0,0), so we need to shift it by (min_voxel - 1) * voxel_dims
            # since we padded the mask
            verts = verts + (min_voxel - 1) * self.voxel_dims

            # Calculate mesh bounds (will be used for limits instead of voxel bounds)
            mesh_min = np.min(verts, axis=0)
            mesh_max = np.max(verts, axis=0)
            mesh_extent = mesh_max - mesh_min
            mesh_center = (mesh_min + mesh_max) / 2

            # Create mesh info
            mesh_info = {
                "verts": verts,
                "faces": faces,
                "min": mesh_min,
                "max": mesh_max,
                "center": mesh_center,
                "extent": mesh_extent
            }

            if self.debug:
                print(f"Component {component_idx} mesh has {len(verts)} vertices, {len(faces)} faces")
                print(f"  Mesh bounds: min={mesh_min}, max={mesh_max}")
                print(f"  Mesh center: {mesh_center}")
                print(f"  Mesh extent: {mesh_extent}")
                print(f"  Voxel bounds: min={min_real}, max={max_real}")
        except Exception as e:
            print(f"Error precomputing mesh for component {component_idx}: {str(e)}")
            mesh_info = None

        # Get regionprops for this component for the inertia tensor
        props = regionprops(component_mask.astype(int))
        if props:
            props = props[0]
            # Compute eigenvalues and eigenvectors from inertia tensor
            if hasattr(props, 'inertia_tensor'):
                eigenvalues, eigenvectors = compute_eigenvectors_from_inertia(props.inertia_tensor)
                # Adjust eigenvalues for voxel dimensions
                adjusted_eigenvalues = eigenvalues * (self.voxel_dims ** 2)

                # Store eigenvector information
                eigenvector_info = {
                    "eigenvalues": eigenvalues,
                    "eigenvectors": eigenvectors,
                    "adjusted_eigenvalues": adjusted_eigenvalues
                }
            else:
                eigenvector_info = None
        else:
            eigenvector_info = None

        # Calculate local limits with margin - use mesh bounds if available
        local_limits = []
        if mesh_info is not None:
            # Use mesh bounds for more accurate limits
            for dim in range(3):
                center = mesh_info["center"][dim]
                half_extent = mesh_info["extent"][dim] * self.margin_factor / 2
                local_limits.append((center - half_extent, center + half_extent))
        else:
            # Fallback to voxel bounds
            for dim in range(3):
                margin = extent[dim] * (self.margin_factor - 1) / 2
                local_limits.append((min_real[dim] - margin, max_real[dim] + margin))

        result = {
            "empty": False,
            "local_limits": local_limits,
            "centroid_voxel": centroid_voxel,
            "centroid_real": centroid_real,
            "min_voxel": min_voxel,
            "max_voxel": max_voxel,
            "min_real": min_real,
            "max_real": max_real,
            "extent": extent,
            "mesh_info": mesh_info,
            "eigenvector_info": eigenvector_info
        }

        if self.debug:
            print(f"Component {component_idx} info:")
            print(f"  Centroid (voxel): {centroid_voxel}")
            print(f"  Centroid (real): {centroid_real}")
            print(f"  Min bounds (voxel): {min_voxel}")
            print(f"  Max bounds (voxel): {max_voxel}")
            print(f"  Min bounds (real): {min_real}")
            print(f"  Max bounds (real): {max_real}")
            print(f"  Extent: {extent}")
            print(f"  Local limits: {local_limits}")
            if eigenvector_info:
                print(f"  Eigenvalues: {eigenvector_info['eigenvalues']}")
                print(f"  Adjusted eigenvalues: {eigenvector_info['adjusted_eigenvalues']}")
                print(f"  Eigenvectors:\n{eigenvector_info['eigenvectors']}")

        return result

    def calculate_global_limits(self):
        """Calculate global axis limits for consistent scaling across all components."""
        all_mesh_centers = []
        all_mesh_extents = []

        for component_idx in range(1, self.num_components + 1):
            if component_idx in self.component_info:
                info = self.component_info[component_idx]
                if "empty" in info and info["empty"]:
                    continue

                # Prefer mesh bounds if available
                if "mesh_info" in info and info["mesh_info"] is not None:
                    mesh_info = info["mesh_info"]
                    all_mesh_centers.append(mesh_info["center"])
                    all_mesh_extents.append(mesh_info["extent"])
                elif "centroid_real" in info and "extent" in info:
                    all_mesh_centers.append(info["centroid_real"])
                    all_mesh_extents.append(info["extent"])

        # Calculate global min/max for consistent axis scaling
        if all_mesh_centers:
            all_mesh_centers = np.array(all_mesh_centers)
            all_mesh_extents = np.array(all_mesh_extents)

            # Maximum extent across all dimensions
            max_extent = np.max(all_mesh_extents) * self.margin_factor

            # Global limits
            self.global_limits = []
            for dim in range(3):
                center = np.mean(all_mesh_centers[:, dim])
                self.global_limits.append((center - max_extent / 2, center + max_extent / 2))

            if self.debug:
                print(f"Global limits: {self.global_limits}")
        else:
            # Default limits if no valid components
            self.global_limits = [(-10, 10), (-10, 10), (-10, 10)]

    def draw_component(self):
        """Draw the current component."""
        # Clear the axes
        self.ax.clear()

        # Get the component index
        component_idx = self.current_cc_idx

        # Skip if out of range
        if component_idx < 1 or component_idx > self.num_components:
            self.ax.text(0, 0, 0, "No component selected", fontsize=14, ha='center')
            self.fig.canvas.draw_idle()
            return

        # Update title
        self.ax.set_title(f'Component {component_idx} of {self.num_components}')

        # Check if component is being processed or not available yet
        if component_idx not in self.component_info:
            self.ax.text(0, 0, 0, f"Component {component_idx} is being processed...",
                         fontsize=14, ha='center', va='center')
            self.fig.canvas.draw_idle()
            return

        # Check if component was processed as empty
        if self.component_info[component_idx].get("empty", False):
            self.ax.text(0, 0, 0, f"Component {component_idx} is empty", fontsize=14, ha='center')
            self.fig.canvas.draw_idle()
            return

        # Get precomputed info for this component
        comp_info = self.component_info[component_idx]

        # Get real-world centroid
        if "centroid_real" in comp_info:
            centroid_real = comp_info["centroid_real"]
        else:
            # Fallback if not precomputed
            component_mask = (self.labeled_components == component_idx)
            props = regionprops(component_mask.astype(int))
            if props and len(props) > 0:
                centroid_voxel = np.array(props[0].centroid)
                centroid_real = centroid_voxel * self.voxel_dims
            else:
                centroid_real = np.array([0, 0, 0])

        # Print debug information
        if self.debug:
            print(f"\nDrawing component {component_idx}:")
            print(f"  Precomputed centroid (real): {centroid_real}")

        # Assign color for this component
        color = self.cm(component_idx / self.num_components)

        # Draw component elements
        try:
            # Draw mesh if available
            if "mesh_info" in comp_info and comp_info["mesh_info"] is not None:
                mesh_info = comp_info["mesh_info"]
                verts = mesh_info["verts"]
                faces = mesh_info["faces"]

                # Simplify mesh if requested
                if self.mesh_simplify < 1.0 and len(faces) > 0:
                    keep_faces = max(1, int(len(faces) * self.mesh_simplify))
                    faces = faces[:keep_faces]

                if self.debug:
                    print(f"  Using precomputed mesh with {len(verts)} vertices and {len(faces)} faces")
                    print(f"  Mesh bounds: min={np.min(verts, axis=0)}, max={np.max(verts, axis=0)}")

                # Plot mesh as wireframe or surface
                self.ax.plot_trisurf(verts[:, 0], verts[:, 1], verts[:, 2],
                                     triangles=faces, color=color, alpha=self.alpha,
                                     linewidth=0.5, edgecolor='black' if self.alpha > 0.6 else color,
                                     shade=True)

                # Draw min/max points of the mesh for debugging
                if self.debug:
                    min_point = np.min(verts, axis=0)
                    max_point = np.max(verts, axis=0)
                    self.ax.scatter(min_point[0], min_point[1], min_point[2],
                                    color='cyan', s=50, alpha=1.0, marker='s')
                    self.ax.scatter(max_point[0], max_point[1], max_point[2],
                                    color='magenta', s=50, alpha=1.0, marker='s')
                    print(f"  Min point (mesh): {min_point}")
                    print(f"  Max point (mesh): {max_point}")

            # Draw component centroid
            self.ax.scatter(centroid_real[0], centroid_real[1], centroid_real[2],
                            color='black', s=100, alpha=1.0, marker='o')

            if self.debug:
                print(f"  Drawing centroid at: {centroid_real}")

            # Draw eigenvectors if available
            if "eigenvector_info" in comp_info and comp_info["eigenvector_info"] is not None:
                eigenvector_info = comp_info["eigenvector_info"]
                eigenvalues = eigenvector_info["eigenvalues"]
                eigenvectors = eigenvector_info["eigenvectors"]
                adjusted_eigenvalues = eigenvector_info["adjusted_eigenvalues"]

                # Draw eigenvectors as arrows, scaled by eigenvalues
                for i in range(len(eigenvalues)):
                    # Calculate arrow length based on eigenvalue
                    arrow_length = np.sqrt(adjusted_eigenvalues[i]) * self.scale_factor

                    # Get direction from eigenvector
                    direction = eigenvectors[:, i]

                    # Ensure the vector is pointing outward from the origin
                    if i == 0 and np.sum(direction) < 0:
                        direction = -direction  # Flip direction for aesthetics

                    # Draw arrow
                    self.ax.quiver(centroid_real[0], centroid_real[1], centroid_real[2],
                                   direction[0] * arrow_length,
                                   direction[1] * arrow_length,
                                   direction[2] * arrow_length,
                                   color='red' if i == 0 else 'green' if i == 1 else 'blue',
                                   alpha=1.0, linewidth=2,
                                   arrow_length_ratio=0.1)

                    # Add text label for eigenvalue
                    endpoint = centroid_real + direction * arrow_length
                    self.ax.text(endpoint[0], endpoint[1], endpoint[2],
                                 f"λ{i + 1}={adjusted_eigenvalues[i]:.2f}",
                                 color='black', fontsize=8)

                if self.debug:
                    print(f"  Drew {len(eigenvalues)} eigenvectors")
            else:
                # No eigenvector info available
                print(f"Component {component_idx} missing eigenvector data")

            print(f"Successfully processed component {component_idx}")

        except Exception as e:
            print(f"Error displaying component {component_idx}: {str(e)}")

            # Use precomputed center for error message
            if "centroid_real" in comp_info:
                center = comp_info["centroid_real"]
            else:
                center = np.array([0, 0, 0])

            self.ax.text(center[0], center[1], center[2],
                         f"Component {component_idx}\nError: {str(e)}",
                         fontsize=14, ha='center', va='center')

        # Set labels
        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')
        self.ax.set_zlabel('Z (mm)')

        # Set equal aspect ratio
        self.ax.set_box_aspect([1, 1, 1])

        # Set axis limits - either global or local
        if self.use_global_limits:
            # Use global limits for consistency across components
            if self.global_limits:
                self.ax.set_xlim(self.global_limits[0])
                self.ax.set_ylim(self.global_limits[1])
                self.ax.set_zlim(self.global_limits[2])

                if self.debug:
                    print(f"  Using global limits: {self.global_limits}")
        else:
            # Use local limits to focus on this component
            if "local_limits" in comp_info:
                local_limits = comp_info["local_limits"]
                self.ax.set_xlim(local_limits[0])
                self.ax.set_ylim(local_limits[1])
                self.ax.set_zlim(local_limits[2])

                if self.debug:
                    print(f"  Using local limits: {local_limits}")

        # Update the figure
        self.fig.canvas.draw_idle()

    def prev_component(self, event):
        if self.current_cc_idx > 1:
            self.current_cc_idx -= 1
            self.slider.set_val(self.current_cc_idx)
            self.draw_component()

    def next_component(self, event):
        if self.current_cc_idx < self.num_components:
            self.current_cc_idx += 1
            self.slider.set_val(self.current_cc_idx)
            self.draw_component()

    def slider_update(self, val):
        self.current_cc_idx = int(val)
        self.draw_component()


def interactive_cc_viewer(cc_mask_file, scale_factor=1.0, colormap='viridis', alpha=0.3, mesh_simplify=0.2,
                          use_global_limits=False, margin_factor=2.5, debug=False, interior_mesh=True):
    """
    Launch an interactive viewer for connected components.

    Parameters:
    -----------
    cc_mask_file : str
        Path to the NIFTI file containing connected components
    scale_factor : float, optional
        Factor to scale eigenvectors for better visualization
    colormap : str, optional
        Matplotlib colormap name to use for components
    alpha : float, optional
        Transparency level for the wireframe meshes (0-1)
    mesh_simplify : float, optional
        Simplification factor for meshes (0-1, lower means more simplified)
    use_global_limits : bool, optional
        Whether to use global limits for all components (True) or local limits for each component (False)
    margin_factor : float, optional
        Factor to determine margin around components (1.0 = no margin, 2.0 = 100% margin)
    debug : bool, optional
        Enable debug print statements
    interior_mesh : bool, optional
        Whether to show interior mesh details
    """
    viewer = CCViewer(cc_mask_file, scale_factor, colormap, alpha, mesh_simplify,
                      use_global_limits, margin_factor, debug, interior_mesh)
    plt.show()
    return viewer


def main():
    parser = argparse.ArgumentParser(description='Interactive viewer for connected components with eigenvectors in 3D')
    parser.add_argument('--cc_mask', '-c', required=True,
                        help='Path to the mask NIFTI file containing connected components')
    parser.add_argument('--scale_factor', '-s', type=float, default=1.0,
                        help='Factor to scale eigenvectors for better visualization (default: 1.0)')
    parser.add_argument('--colormap', '-cm', default='viridis',
                        help='Matplotlib colormap to use (default: viridis)')
    parser.add_argument('--alpha', '-a', type=float, default=0.3,
                        help='Transparency level for wireframe meshes (default: 0.3)')
    parser.add_argument('--mesh_simplify', '-ms', type=float, default=0.2,
                        help='Simplification factor for meshes (0-1, lower means more simplified) (default: 0.2)')
    parser.add_argument('--global_limits', '-g', action='store_true',
                        help='Use global limits for all components (default: use local limits for each component)')
    parser.add_argument('--margin_factor', '-m', type=float, default=2.5,
                        help='Factor to determine margin around components (default: 2.5)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug print statements')
    parser.add_argument('--interior', '-i', action='store_true',
                        help='Show interior mesh details')

    args = parser.parse_args()

    interactive_cc_viewer(
        args.cc_mask,
        args.scale_factor,
        args.colormap,
        args.alpha,
        args.mesh_simplify,
        args.global_limits,
        args.margin_factor,
        args.debug,
        args.interior
    )


if __name__ == "__main__":
    main()