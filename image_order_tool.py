import os
import shutil
import time
import logging
import traceback
from tkinter import Tk, Toplevel, filedialog, Label, Button, Entry, Frame, Scrollbar, Canvas, messagebox, VERTICAL, HORIZONTAL, RIGHT, LEFT, BOTH, Y, X, BOTTOM, TOP, PanedWindow
from PIL import Image, ImageTk


# ============================================================================
# UI CONSTANTS & STYLING
# ============================================================================

class UIConstants:
    """Centralized UI styling constants."""
    # Fonts
    FONT_TITLE = ('Arial', 11, 'bold')
    FONT_HEADER = ('Arial', 10, 'bold')
    FONT_LABEL = ('Arial', 9)
    FONT_SMALL = ('Arial', 8)
    FONT_XSMALL = ('Arial', 7)
    
    # Padding
    PAD_STANDARD = 8
    PAD_SMALL = 4
    PAD_MINI = 2
    
    # Sizing
    THUMB_SIZE = (100, 100)
    PREVIEW_MIN_WIDTH = 300
    PREVIEW_MIN_HEIGHT = 200
    MAGNIFIER_CROP_SIZE = 90
    MAGNIFIER_DISPLAY_SIZE = 240
    MAGNIFIER_WINDOW_SIZE = 260
    
    # Folders
    LOG_FOLDER = "Logs"
    OUTPUT_FOLDER = "corrected"
    
    # File extensions
    IMAGE_FORMATS = ('.jpg', '.jpeg', '.png')


class ImageProcessor:
    """Handles image loading, resizing, and thumbnail creation."""
    
    @staticmethod
    def get_resample_filter():
        """Return the appropriate image resampling filter based on PIL version."""
        if hasattr(Image, 'Resampling'):
            return Image.Resampling.LANCZOS
        return Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BICUBIC
    
    @staticmethod
    def load_and_resize_image(img_path, max_size=None):
        """Load an image and optionally resize it.
        
        Args:
            img_path: Path to the image file
            max_size: Tuple (width, height) for max dimensions, or None for no resize
            
        Returns:
            PIL Image object, or None if loading fails
        """
        try:
            img = Image.open(img_path)
            if max_size:
                img_width, img_height = img.size
                max_width, max_height = max_size
                if img_width > max_width or img_height > max_height:
                    ratio = min(max_width / img_width, max_height / img_height)
                    new_size = (int(img_width * ratio), int(img_height * ratio))
                    img = img.resize(new_size, ImageProcessor.get_resample_filter())
            return img
        except Exception as e:
            logging.getLogger("ImageOrderToolLogger").error(f"Failed to load image: {img_path} - {type(e).__name__}: {str(e)}")
            return None
    
    @staticmethod
    def create_thumbnail(img_path, thumb_size=(100, 100)):
        """Create a thumbnail ImageTk.PhotoImage from an image file.
        
        Args:
            img_path: Path to the image file
            thumb_size: Tuple (width, height) for thumbnail
            
        Returns:
            ImageTk.PhotoImage object, or None if creation fails
        """
        try:
            img = Image.open(img_path)
            img.thumbnail(thumb_size)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            logging.getLogger("ImageOrderToolLogger").error(f"Failed to create thumbnail: {img_path} - {type(e).__name__}: {str(e)}")
            return None


class LoggerManager:
    """Manages logging configuration and operations."""
    
    def __init__(self, log_folder=None):
        """Initialize logger manager.
        
        Args:
            log_folder: Folder to store log files. If None, uses 'Logs' in current directory.
        """
        self.log_folder = log_folder or os.path.join(os.getcwd(), UIConstants.LOG_FOLDER)
        os.makedirs(self.log_folder, exist_ok=True)
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Create and configure the logger.
        
        Returns:
            Configured logger object
        """
        logger = logging.getLogger("ImageOrderToolLogger")
        logger.setLevel(logging.INFO)
        log_file = os.path.join(self.log_folder, f"log_{time.strftime('%Y%m%d_%H%M%S')}.txt")
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(fh)
        return logger
    
    def log_correction(self, folder_path, before_files, after_files, final_files, duration, output_folder):
        """Log the correction operation with detailed information.
        
        Args:
            folder_path: Source folder path
            before_files: List of original filenames
            after_files: List of serial-numbered filenames
            final_files: List of corrected filenames (before serial renaming)
            duration: Processing duration in seconds
            output_folder: Output folder path
        """
        log_msg = (
            f"Subfolder: {folder_path}\n"
            f"Total images: {len(before_files)}\n"
            f"Filenames before: {before_files}\n"
            f"Filenames after: {after_files}\n"
            f"Duration: {duration:.2f} seconds\n"
            f"Corrected folder: {output_folder}\n"
        )
        self.logger.info(log_msg)
    
    def log_error(self, error_msg, exception=None):
        """Log error messages with optional exception details.
        
        Args:
            error_msg: Error message description
            exception: Optional exception object for stack trace
        """
        if exception:
            self.logger.error(f"{error_msg}\nException: {type(exception).__name__}: {str(exception)}")
            self.logger.error(f"Stack Trace:\n{traceback.format_exc()}")
        else:
            self.logger.error(error_msg)
    
    def log_crash(self, crash_msg, exception=None):
        """Log critical crash events with full details.
        
        Args:
            crash_msg: Crash description
            exception: Optional exception object
        """
        crash_log = f"CRASH EVENT: {crash_msg}"
        if exception:
            crash_log += f"\nException Type: {type(exception).__name__}\nMessage: {str(exception)}"
            crash_log += f"\nFull Traceback:\n{traceback.format_exc()}"
        self.logger.critical(crash_log)
    
    def log_interruption(self, action, details=""):
        """Log user interruptions or cancellations.
        
        Args:
            action: Action that was interrupted
            details: Additional details about the interruption
        """
        msg = f"INTERRUPTION: {action} was cancelled by user"
        if details:
            msg += f" - {details}"
        self.logger.warning(msg)


class ImageOrderLogic:
    """Handles business logic for image reordering and pair creation."""
    
    @staticmethod
    def get_image_files(folder_path):
        """Get list of image files from folder, sorted.
        
        Args:
            folder_path: Path to folder containing images
            
        Returns:
            List of sorted image filenames
        """
        files = [f for f in os.listdir(folder_path)
                if f.lower().endswith(UIConstants.IMAGE_FORMATS)]
        return sorted(files)
    
    @staticmethod
    def correct_image_order(all_files, first_count, last_count):
        """Reorder intermediate images from back-front to front-back pattern.
        
        Args:
            all_files: List of all image filenames
            first_count: Number of correctly-ordered images at the start
            last_count: Number of correctly-ordered images at the end
            
        Returns:
            List of corrected filenames
        """
        total = len(all_files)
        interm_start = first_count
        interm_end = total - last_count
        
        if interm_start >= interm_end:
            return all_files
        
        interm_files = all_files[interm_start:interm_end]
        interm_corrected = []
        
        # Swap pairs: (0,1) → (1,0), (2,3) → (3,2), etc.
        for i in range(0, len(interm_files), 2):
            if i + 1 < len(interm_files):
                interm_corrected.append(interm_files[i + 1])
            interm_corrected.append(interm_files[i])
        
        return all_files[:interm_start] + interm_corrected + all_files[interm_end:]
    
    @staticmethod
    def create_preview_pairs(all_files, corrected_files):
        """Create before/after image pairs for preview.
        
        Args:
            all_files: Original filenames list
            corrected_files: Corrected filenames list
            
        Returns:
            List of tuples: [(before_pair, after_pair), ...]
        """
        max_pairs = max((len(all_files) + 1) // 2, (len(corrected_files) + 1) // 2)
        pairs = []
        
        for i in range(max_pairs):
            before_pair = [
                all_files[2*i] if 2*i < len(all_files) else None,
                all_files[2*i+1] if 2*i+1 < len(all_files) else None
            ]
            after_pair = [
                corrected_files[2*i] if 2*i < len(corrected_files) else None,
                corrected_files[2*i+1] if 2*i+1 < len(corrected_files) else None
            ]
            pairs.append((before_pair, after_pair))
        
        return pairs
    
    @staticmethod
    def copy_and_rename_files(folder_path, corrected_files, output_folder, logger_manager=None):
        """Copy corrected files to output folder with serial number prefix.
        
        Args:
            folder_path: Source folder path
            corrected_files: List of corrected filenames in new order
            output_folder: Destination folder path
            logger_manager: Optional LoggerManager for error logging
        """
        try:
            os.makedirs(output_folder, exist_ok=True)
            for idx, fname in enumerate(corrected_files):
                try:
                    src = os.path.join(folder_path, fname)
                    dst = os.path.join(output_folder, f"{idx+1}_{fname}")
                    shutil.copy2(src, dst)
                except Exception as e:
                    error_msg = f"Failed to copy file {fname}: {type(e).__name__}: {str(e)}"
                    if logger_manager:
                        logger_manager.log_error(error_msg, e)
                    else:
                        logging.getLogger("ImageOrderToolLogger").error(error_msg)
                    raise
        except Exception as e:
            error_msg = f"File copying operation failed: {type(e).__name__}: {str(e)}"
            if logger_manager:
                logger_manager.log_error(error_msg, e)
            else:
                logging.getLogger("ImageOrderToolLogger").error(error_msg)
            raise


class WidgetHelper:
    """Helper class for creating common widgets with consistent styling."""
    
    @staticmethod
    def create_label(parent, text, bg, fg, font=UIConstants.FONT_LABEL, **kwargs):
        """Create a styled label."""
        return Label(parent, text=text, bg=bg, fg=fg, font=font, **kwargs)
    
    @staticmethod
    def create_button(parent, text, bg, fg, command=None, height=1, **kwargs):
        """Create a styled button."""
        return Button(parent, text=text, bg=bg, fg=fg, command=command, height=height,
                     font=UIConstants.FONT_LABEL, relief='raised', cursor='hand2', **kwargs)
    
    @staticmethod
    def create_entry(parent, width=4, **kwargs):
        """Create a styled entry."""
        return Entry(parent, width=width, font=UIConstants.FONT_LABEL,
                    relief='solid', borderwidth=1, **kwargs)
    
    @staticmethod
    def create_frame(parent, bg, relief='solid', borderwidth=1):
        """Create a styled frame."""
        return Frame(parent, bg=bg, relief=relief, borderwidth=borderwidth)


class GUIBuilder:
    """Provides static methods for building GUI components."""
    
    @staticmethod
    def create_control_section(parent, colors):
        """Create the control panel section with buttons and status.
        
        Args:
            parent: Parent frame
            colors: Color palette dictionary
            
        Returns:
            Tuple of (info_label, intermediate_label, status_label, first_entry, last_entry, select_btn, update_btn, run_btn, reset_btn)
        """
        parent.configure(bg='white')
        
        # Folder info section
        info_frame = WidgetHelper.create_frame(parent, colors['bg_light'])
        info_frame.pack(pady=UIConstants.PAD_STANDARD, padx=UIConstants.PAD_STANDARD, fill=X)
        info_label = WidgetHelper.create_label(info_frame, "📁 No folder selected.",
                                               colors['bg_light'], colors['text_primary'],
                                               wraplength=280, justify='left',
                                               padx=UIConstants.PAD_STANDARD,
                                               pady=6)
        info_label.pack(fill=X)
        
        # Primary button
        select_btn = Button(parent, text="📂 Select Folder", height=2, bg=colors['primary'], fg='white',
                           font=UIConstants.FONT_HEADER, relief='flat', cursor='hand2',
                           activebackground='#1976D2')
        select_btn.pack(pady=UIConstants.PAD_SMALL, padx=UIConstants.PAD_STANDARD, fill=X)
        
        # Counts section
        counts_label = WidgetHelper.create_label(parent, "Image Count Configuration",
                                                 'white', colors['text_primary'],
                                                 font=UIConstants.FONT_HEADER,
                                                 padx=UIConstants.PAD_STANDARD,
                                                 pady=UIConstants.PAD_STANDARD)
        counts_label.pack(anchor='w')
        
        counts_frame = WidgetHelper.create_frame(parent, 'white', relief='flat', borderwidth=0)
        counts_frame.pack(pady=UIConstants.PAD_MINI, padx=UIConstants.PAD_STANDARD, fill=X)
        
        WidgetHelper.create_label(counts_frame, "First:", 'white', colors['text_secondary']).grid(
            row=0, column=0, sticky='w', padx=(0, 4))
        first_entry = WidgetHelper.create_entry(counts_frame, width=4)
        first_entry.grid(row=0, column=1, sticky='w', padx=(0, 12))
        
        WidgetHelper.create_label(counts_frame, "Last:", 'white', colors['text_secondary']).grid(
            row=0, column=2, sticky='w', padx=(0, 4))
        last_entry = WidgetHelper.create_entry(counts_frame, width=4)
        last_entry.grid(row=0, column=3, sticky='w', padx=(0, 12))
        
        update_btn = WidgetHelper.create_button(counts_frame, "Update", colors['bg_dark'],
                                               colors['text_primary'], width=8)
        update_btn.grid(row=0, column=4, sticky='w')
        
        # Intermediate count display
        intermediate_label = WidgetHelper.create_label(parent, "Intermediate: 0 images",
                                                      'white', colors['warning'],
                                                      font=UIConstants.FONT_HEADER,
                                                      padx=UIConstants.PAD_STANDARD,
                                                      pady=UIConstants.PAD_SMALL)
        intermediate_label.pack(anchor='w')
        
        # Run correction (primary action)
        run_btn = Button(parent, text="✓ Run Correction", height=2, bg=colors['success'],
                        fg='white', font=UIConstants.FONT_HEADER, relief='flat',
                        cursor='hand2', activebackground='#45a049')
        run_btn.pack(pady=UIConstants.PAD_STANDARD, padx=UIConstants.PAD_STANDARD, fill=X)
        
        # Secondary button
        reset_btn = WidgetHelper.create_button(parent, "↻ Reset", colors['bg_dark'],
                                              colors['text_primary'], height=1)
        reset_btn.pack(pady=UIConstants.PAD_MINI, padx=UIConstants.PAD_STANDARD, fill=X)
        
        # Status section
        status_frame = WidgetHelper.create_frame(parent, colors['bg_light'])
        status_frame.pack(pady=8, padx=8, fill=BOTH, expand=True)
        
        status_container = Frame(status_frame, bg=colors['bg_light'])
        status_container.pack(fill=BOTH, expand=True, anchor='nw')
        
        status_label = Label(status_container, text="🟢 Ready", bg=colors['bg_light'], fg=colors['success'], font=('Arial', 9, 'bold'), padx=8, pady=6, justify='left')
        status_label.pack(side=LEFT, fill=BOTH, expand=True, anchor='nw')
        
        # Magnifier tool only (removed zoom +/- buttons)
        zoom_frame = Frame(status_frame, bg=colors['bg_light'])
        zoom_frame.pack(side=RIGHT, anchor='e', padx=8, pady=4)
        
        magnifier_btn = Button(zoom_frame, text="🔎 Magnifier", width=12, height=1, bg=colors['bg_dark'], fg=colors['text_primary'], font=('Arial', 9, 'bold'), relief='raised', cursor='hand2')
        magnifier_btn.pack(side=LEFT, padx=1)
        
        # Store magnifier button reference for parent to connect callbacks
        status_label._magnifier = magnifier_btn
        
        # Keyboard hints
        hints_frame = Frame(parent, bg=colors['bg_light'], relief='solid', borderwidth=1)
        hints_frame.pack(pady=8, padx=8, fill=X)
        hints_label = Label(hints_frame, text="⌨️ Click thumbnail to view | Use Magnifier 🔎 to inspect details | Drag panes to resize", bg=colors['bg_light'], fg=colors['text_secondary'], font=('Arial', 8), padx=8, pady=4, justify='left')
        hints_label.pack(fill=X)
        
        return info_label, intermediate_label, status_label, first_entry, last_entry, select_btn, update_btn, run_btn, reset_btn


class ImageOrderTool:
    """Main controller for the image ordering application."""
    
    def __init__(self, master):
        """Initialize the application.
        
        Args:
            master: Tkinter root window
        """
        self.master = master
        self.master.title("Manuscript Image Order Tool")
        self.master.configure(bg='#ffffff')
        
        # UI Colors
        self.colors = {
            'primary': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'bg_light': '#f5f5f5',
            'bg_dark': '#e0e0e0',
            'text_primary': '#212121',
            'text_secondary': '#757575',
            'border': '#bdbdbd'
        }
        
        # Data
        self.folder_path = ''
        self.image_files = []
        self.first_count = 0
        self.last_count = 0
        self.start_time = None
        self._preview_pairs = []
        self._preview_pair_idx = 0
        self._preview_thumbs = []
        self._preview_updating = False  # Recursion guard flag
        self._preview_resize_after_id = None  # Debounce id for resize redraw
        self._preview_last_size = (0, 0)  # Last rendered preview area size
        self._magnifier_active = False  # Magnifier tool state
        self._magnifier_window = None  # Magnifier window reference
        self._corrected_files = []  # Store corrected files for on-demand preview
        self._current_preview_labels = {}  # Store label references with image file names
        
        # UI references
        self.canvas = None
        self.scroll_y = None
        self.frame = None
        self.thumb_labels = []
        self.thumbnails = []
        
        # Managers
        self.logger_manager = LoggerManager()
        
        # Init UI
        self.init_gui()
    
    def init_gui(self):
        """Initialize the GUI layout with three-panel design."""
        # Main container
        main_container = Frame(self.master, bg='white')
        main_container.pack(fill=BOTH, expand=True)
        
        # Main horizontal split using PanedWindow for resizable sections
        main_pane = PanedWindow(main_container, orient=HORIZONTAL, sashrelief='raised', sashwidth=6, bg='white')
        main_pane.pack(fill=BOTH, expand=True)

        # Left vertical split using PanedWindow
        left_pane = PanedWindow(main_pane, orient=VERTICAL, sashrelief='raised', sashwidth=6, bg='white')
        main_pane.add(left_pane, minsize=350)

        # Right frame for corrected preview
        right_frame = Frame(main_pane, bg=self.colors['bg_light'], relief='flat', borderwidth=0)
        main_pane.add(right_frame, minsize=350)

        # Left-Top: Thumbnails label + scroll area
        thumb_header = Frame(left_pane, bg=self.colors['bg_dark'], height=35)
        left_pane.add(thumb_header, minsize=35)
        thumb_header.pack_propagate(False)
        thumb_label = Label(thumb_header, text="Image Gallery", bg=self.colors['bg_dark'], fg=self.colors['text_primary'], font=('Arial', 11, 'bold'), padx=10, pady=5)
        thumb_label.pack(side=LEFT, anchor='w')
        
        thumb_frame = Frame(left_pane, bg='white')
        left_pane.add(thumb_frame, minsize=200)
        self.canvas = Canvas(thumb_frame, width=350, height=350, bg='white', highlightthickness=0)
        self.scroll_y = Scrollbar(thumb_frame, orient=VERTICAL, command=self.canvas.yview)
        self.frame = Frame(self.canvas, bg='white')
        self.frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.scroll_y.pack(side=RIGHT, fill=Y)
        self._selected_thumb_idx = None

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all('<MouseWheel>', _on_mousewheel)

        # Left-Bottom: Controls
        controls_frame = Frame(left_pane, bg='white')
        left_pane.add(controls_frame, minsize=250)
        (self.info_label, self.intermediate_label, self.status_label,
         self.first_entry, self.last_entry, select_btn, update_btn, run_btn, reset_btn) = GUIBuilder.create_control_section(controls_frame, self.colors)
        
        # Connect button callbacks
        select_btn.config(command=self.select_folder)
        update_btn.config(command=self.update_counts)
        run_btn.config(command=self.run_correction)
        reset_btn.config(command=self.reset)
        
        # Connect magnifier button callback only
        self.status_label._magnifier.config(command=self._toggle_magnifier)
        
        # Right frame header
        self._right_header = Frame(right_frame, bg=self.colors['bg_dark'], height=35)
        self._right_header.pack(side=TOP, fill=X)
        self._right_header.pack_propagate(False)
        right_label = Label(self._right_header, text="Before / After Preview", bg=self.colors['bg_dark'], fg=self.colors['text_primary'], font=('Arial', 11, 'bold'), padx=10, pady=5)
        right_label.pack(side=LEFT, anchor='w')
        
        # Compare Corrected Files button
        self._compare_btn = Button(self._right_header, text="📊 Compare Corrected Files", bg=self.colors['primary'], fg='white', font=('Arial', 9, 'bold'), relief='flat', cursor='hand2', state='disabled')
        self._compare_btn.pack(side=RIGHT, padx=8, pady=4)
        self._compare_btn.config(command=self._compare_corrected_files)
        
        # Store reference to right frame for preview
        self.corrected_preview_label = Label(right_frame, text="Select folder and run correction to see preview.", bg=self.colors['bg_light'], fg=self.colors['text_secondary'], font=('Arial', 10))
        self.corrected_preview_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self._right_frame = right_frame
        
        # Bind resize event to update preview dynamically
        self._right_frame.bind('<Configure>', self._on_preview_resize)
    
    def _on_preview_resize(self, event=None):
        """Handle preview area resize with debounced redraw to avoid flicker loops."""
        if not self._preview_pairs or self._preview_updating:
            return

        width = self._right_frame.winfo_width()
        height = self._right_frame.winfo_height()
        last_width, last_height = self._preview_last_size

        # Ignore tiny changes that happen during internal layout churn.
        if abs(width - last_width) < 8 and abs(height - last_height) < 8:
            return

        if self._preview_resize_after_id:
            try:
                self.master.after_cancel(self._preview_resize_after_id)
            except Exception:
                pass

        self._preview_resize_after_id = self.master.after(120, self._preview_refresh_after_resize)

    def _preview_refresh_after_resize(self):
        """Run the delayed preview refresh after resize debounce window."""
        self._preview_resize_after_id = None
        if self._preview_pairs and not self._preview_updating:
            self._preview_update()
    
    def _toggle_magnifier(self):
        """Toggle magnifier tool on/off."""
        self._magnifier_active = not self._magnifier_active
        if self._magnifier_active:
            # Activate magnifier
            self.status_label._magnifier.config(bg=self.colors['success'], fg='white')
            self.status_label.config(text="🔎 Magnifier ON - Move mouse over images", fg=self.colors['success'])
            # Bind to the canvas area where preview is shown
            self._right_frame.bind('<Motion>', self._on_magnifier_motion)
            self._right_frame.bind('<Leave>', self._hide_magnifier)
            self._set_preview_image_cursor('crosshair')
            self.logger_manager.logger.info("Magnifier tool activated")
        else:
            # Deactivate magnifier
            self.status_label._magnifier.config(bg=self.colors['bg_dark'], fg=self.colors['text_primary'])
            self.status_label.config(text="🟢 Ready", fg=self.colors['success'])
            self._right_frame.unbind('<Motion>')
            self._right_frame.unbind('<Leave>')
            self._set_preview_image_cursor('arrow')
            self._hide_magnifier(None)
            self.logger_manager.logger.info("Magnifier tool deactivated")
    
    def _on_magnifier_motion(self, event):
        """Handle mouse motion for magnifier - magnify image area under cursor."""
        try:
            if not self._magnifier_active or not self._preview_pairs:
                return
            
            # Use absolute pointer coordinates so this works for events from child labels too.
            x_root = event.x_root
            y_root = event.y_root
            
            widget = getattr(event, 'widget', None) or self.master.winfo_containing(x_root, y_root)
            if widget and not hasattr(widget, '_image_filename'):
                widget = self.master.winfo_containing(x_root, y_root)
            if not widget:
                self._hide_magnifier(None)
                return
            
            # Check if this is an image label with stored image data
            if not hasattr(widget, '_image_filename'):
                self._hide_magnifier(None)
                return
            
            img_filename = widget._image_filename
            
            try:
                # Load the full resolution image
                img_path = os.path.join(self.folder_path, img_filename)
                full_img = Image.open(img_path)
                img_width, img_height = full_img.size
                
                # Get label dimensions for coordinate mapping
                label_width = widget.winfo_width()
                label_height = widget.winfo_height()
                
                if label_width <= 1 or label_height <= 1:
                    return
                
                # Get cursor position relative to label
                label_x = x_root - widget.winfo_rootx()
                label_y = y_root - widget.winfo_rooty()
                
                # Check bounds
                if label_x < 0 or label_y < 0 or label_x >= label_width or label_y >= label_height:
                    self._hide_magnifier(None)
                    return
                
                # Map label coordinates to image coordinates
                img_x = int((label_x / label_width) * img_width)
                img_y = int((label_y / label_height) * img_height)
                
                # Clamp to image bounds
                img_x = max(0, min(img_x, img_width - 1))
                img_y = max(0, min(img_y, img_height - 1))
                
                # Larger crop radius gives a less aggressive zoom feel.
                crop_radius = UIConstants.MAGNIFIER_CROP_SIZE
                left = max(0, img_x - crop_radius)
                top = max(0, img_y - crop_radius)
                right = min(img_width, img_x + crop_radius)
                bottom = min(img_height, img_y + crop_radius)
                
                # Crop the region from original image
                cropped = full_img.crop((left, top, right, bottom))
                cropped_w, cropped_h = cropped.size
                
                # Display using configured magnifier size.
                magnified = cropped.resize((UIConstants.MAGNIFIER_DISPLAY_SIZE, UIConstants.MAGNIFIER_DISPLAY_SIZE), ImageProcessor.get_resample_filter())
                
                # Convert to PhotoImage
                magnified_photo = ImageTk.PhotoImage(magnified)
                
                # Create or update magnifier window
                if self._magnifier_window is None:
                    self._magnifier_window = Toplevel(self.master)
                    self._magnifier_window.attributes('-topmost', True)
                    self._magnifier_window.overrideredirect(True)
                    self._magnifier_canvas = Canvas(self._magnifier_window, width=UIConstants.MAGNIFIER_WINDOW_SIZE, height=UIConstants.MAGNIFIER_WINDOW_SIZE, bg='white',
                                                    highlightthickness=0)
                    self._magnifier_canvas.pack()
                else:
                    # Ensure previously withdrawn window is visible again.
                    self._magnifier_window.deiconify()
                
                # Position window at cursor
                self._magnifier_window.geometry(f'{UIConstants.MAGNIFIER_WINDOW_SIZE}x{UIConstants.MAGNIFIER_WINDOW_SIZE}+{x_root + 20}+{y_root + 20}')
                
                # Draw magnified image
                self._magnifier_canvas.delete('all')
                self._magnifier_canvas.create_rectangle(0, 0, UIConstants.MAGNIFIER_WINDOW_SIZE, UIConstants.MAGNIFIER_WINDOW_SIZE, fill='white', outline=self.colors['primary'], width=3)
                center = UIConstants.MAGNIFIER_WINDOW_SIZE // 2
                self._magnifier_canvas.create_image(center, center, image=magnified_photo)
                
                # Draw crosshair
                self._magnifier_canvas.create_line(center, center - 20, center, center + 20, fill=self.colors['warning'], width=2)
                self._magnifier_canvas.create_line(center - 20, center, center + 20, center, fill=self.colors['warning'], width=2)
                
                # Store reference
                self._magnifier_photo = magnified_photo
                
                self._magnifier_window.lift()
                
            except Exception as inner_e:
                self.logger_manager.log_error(f"Error magnifying image {img_filename}", inner_e)
                self._hide_magnifier(None)
        
        except Exception as e:
            self.logger_manager.log_error("Error in magnifier motion handler", e)
            self._hide_magnifier(None)
    
    def _hide_magnifier(self, event):
        """Hide magnifier window."""
        if self._magnifier_window:
            try:
                self._magnifier_window.withdraw()
            except:
                pass
    
    def select_folder(self):
        """Open folder selection dialog and load images."""
        try:
            folder = filedialog.askdirectory()
            if folder:
                self.folder_path = folder
                self.logger_manager.logger.info(f"Selected folder: {self.folder_path}")
                self.start_time = time.time()
                self.load_images()
            else:
                self.logger_manager.log_interruption("Folder selection", "User cancelled folder dialog")
        except Exception as e:
            error_msg = "Error in folder selection"
            self.logger_manager.log_error(error_msg, e)
            self.status_label.config(text="🔴 Error: Failed to select folder", fg=self.colors['error'])
            messagebox.showerror("❌ Error", f"Failed to select folder: {str(e)}")

    def load_images(self):
        """Load images from the selected folder."""
        try:
            self.image_files = ImageOrderLogic.get_image_files(self.folder_path)
            folder_name = os.path.basename(self.folder_path)
            self.info_label.config(text=f"📁 {folder_name}\n{len(self.image_files)} images loaded")
            self.status_label.config(text=f"🟢 {len(self.image_files)} images loaded", fg=self.colors['success'])
            self.first_entry.delete(0, 'end')
            self.last_entry.delete(0, 'end')
            self.first_entry.insert(0, '0')
            self.last_entry.insert(0, '0')
            self.update_counts()
            self.show_thumbnails()
            self.corrected_preview_label.config(text="Corrected preview will appear here.")
            self.logger_manager.logger.info(f"Successfully loaded {len(self.image_files)} images from {self.folder_path}")
        except Exception as e:
            error_msg = f"Error loading images from folder: {self.folder_path}"
            self.logger_manager.log_error(error_msg, e)
            self.status_label.config(text="🔴 Error: Failed to load images", fg=self.colors['error'])
            messagebox.showerror("❌ Error", f"Failed to load images: {str(e)}")

    def show_thumbnails(self):
        """Display thumbnail grid for loaded images with selection feedback."""
        try:
            for lbl in self.thumb_labels:
                lbl.destroy()
            self.thumb_labels = []
            self.thumbnails = []
        except Exception as e:
            error_msg = "Error clearing existing thumbnails"
            self.logger_manager.log_error(error_msg, e)
        
        for idx, img_file in enumerate(self.image_files):
            try:
                img_path = os.path.join(self.folder_path, img_file)
                thumb = ImageProcessor.create_thumbnail(img_path, thumb_size=(100, 100))
                if thumb:
                    # Use a frame for better styling
                    thumb_container = Frame(self.frame, bg='white', relief='solid', borderwidth=1, highlightthickness=2, highlightbackground=self.colors['border'])
                    thumb_container.grid(row=idx//8, column=idx%8, padx=2, pady=2, sticky='nsew')
                    
                    lbl = Label(thumb_container, image=thumb, text=f"{idx+1}", compound='bottom', font=('Arial', 8, 'bold'), bg='white', fg=self.colors['text_primary'])
                    lbl.pack(fill=BOTH, expand=True)
                    lbl.image = thumb
                    
                    # Binding with hover effects
                    def on_enter(e, container=thumb_container):
                        container.configure(bg=self.colors['primary'], highlightbackground=self.colors['primary'])
                        
                    def on_leave(e, container=thumb_container):
                        container.configure(bg='white', highlightbackground=self.colors['border'])
                        
                    def on_click(e, idx=idx, container=thumb_container):
                        try:
                            self._selected_thumb_idx = idx
                            container.configure(bg=self.colors['success'], highlightbackground=self.colors['success'])
                            self.open_full_image(idx)
                        except Exception as click_e:
                            self.logger_manager.log_error(f"Error handling thumbnail click for image {idx}", click_e)
                            messagebox.showerror("❌ Error", f"Failed to open image: {str(click_e)}")
                    
                    lbl.bind("<Enter>", on_enter)
                    lbl.bind("<Leave>", on_leave)
                    lbl.bind("<Button-1>", on_click)
                    
                    self.thumbnails.append(thumb)
                    self.thumb_labels.append(lbl)
            except Exception as e:
                error_msg = f"Error creating thumbnail for image {idx}: {img_file}"
                self.logger_manager.log_error(error_msg, e)

    def open_full_image(self, idx):
        """Open full-image viewer for the image at the given index.
        
        Args:
            idx: Index of image to view
        """
        ImageViewer(self.master, self.folder_path, self.image_files, idx)

    def update_counts(self):
        """Update intermediate image count based on first/last counts."""
        try:
            self.first_count = int(self.first_entry.get())
        except ValueError:
            self.first_count = 0
        try:
            self.last_count = int(self.last_entry.get())
        except ValueError:
            self.last_count = 0
        total = len(self.image_files)
        interm = max(0, total - self.first_count - self.last_count)
        if interm > 0:
            self.intermediate_label.config(text=f"⚠️ Intermediate: {interm} images to reorder", fg=self.colors['warning'])
        else:
            self.intermediate_label.config(text=f"✓ Intermediate: {interm} images", fg=self.colors['success'])

    def run_correction(self):
        """Execute image reordering and save corrected copies."""
        try:
            if not self.folder_path or not self.image_files:
                self.logger_manager.log_interruption("Run correction", "No folder or images loaded")
                messagebox.showerror("❌ Error", "No folder or images loaded.")
                self.status_label.config(text="🔴 Error: No folder loaded", fg=self.colors['error'])
                return
            
            total = len(self.image_files)
            interm = total - self.first_count - self.last_count
            
            if interm < 0:
                self.logger_manager.log_interruption("Run correction", f"Invalid counts: first={self.first_count}, last={self.last_count}, total={total}")
                messagebox.showerror("❌ Error", "Counts exceed total images.")
                self.status_label.config(text="🔴 Error: Invalid counts", fg=self.colors['error'])
                return
            
            # Correct the order
            self.status_label.config(text="⏳ Processing images...", fg=self.colors['text_secondary'])
            self.master.update()
            corrected_files = ImageOrderLogic.correct_image_order(self.image_files, self.first_count, self.last_count)
            
            # Save to output folder
            output_folder = os.path.join(self.folder_path, UIConstants.OUTPUT_FOLDER)
            ImageOrderLogic.copy_and_rename_files(self.folder_path, corrected_files, output_folder, self.logger_manager)
            
            # Log the operation
            before_names = list(self.image_files)
            after_names = [f"{idx+1}_{fname}" for idx, fname in enumerate(corrected_files)]
            duration = time.time() - self.start_time if self.start_time else 0
            self.logger_manager.log_correction(self.folder_path, before_names, after_names, corrected_files, duration, output_folder)
            
            # Update status and clear preview (don't show automatically to prevent blinking)
            self.status_label.config(text=f"✓ Complete in {duration:.2f}s | ✓ Saved to '{UIConstants.OUTPUT_FOLDER}' folder", fg=self.colors['success'])
            self._corrected_files = corrected_files  # Store for on-demand preview
            self._clear_preview()  # Clear and show message instead of auto-preview
            self.logger_manager.logger.info(f"Image correction completed successfully. {total} images processed.")
            messagebox.showinfo("✓ Success", f"✓ {total} images processed\n✓ Saved to '{UIConstants.OUTPUT_FOLDER}' folder\n✓ Compare button enabled!")
        except KeyboardInterrupt:
            self.logger_manager.log_interruption("Run correction", "User pressed Ctrl+C")
            self.status_label.config(text="🔴 Interrupted by user", fg=self.colors['error'])
        except Exception as e:
            error_msg = "Error during image correction process"
            self.logger_manager.log_error(error_msg, e)
            self.status_label.config(text="🔴 Error during processing", fg=self.colors['error'])
            messagebox.showerror("❌ Error", f"Processing failed: {str(e)}\n\nSee log file for details.")

    def show_corrected_preview(self, corrected_files):
        """Display before/after comparison preview.
        
        Args:
            corrected_files: List of corrected filenames
        """
        # Prepare pairs
        self._preview_pairs = ImageOrderLogic.create_preview_pairs(self.image_files, corrected_files)
        self._preview_pair_idx = 0
        self._preview_update()

    def _clear_preview(self):
        """Clear preview area and show a message."""
        try:
            # Destroy all children except header
            children_to_destroy = [w for w in self._right_frame.winfo_children() if w != self._right_header]
            for widget in children_to_destroy:
                try:
                    widget.destroy()
                except:
                    pass
            
            # Show message
            message_frame = Frame(self._right_frame, bg=self.colors['bg_light'])
            message_frame.pack(fill=BOTH, expand=True, pady=20, padx=20)
            
            msg_label = Label(message_frame, 
                             text=f"✓ Corrected files saved to '{UIConstants.OUTPUT_FOLDER}' folder\n\nClick 'Compare Corrected Files' button to view before/after preview", 
                             bg=self.colors['bg_light'], fg=self.colors['success'],
                             font=('Arial', 11), justify='center')
            msg_label.pack(expand=True)
            
            # Enable the Compare button
            self._compare_btn.config(state='normal')
            
        except Exception as e:
            self.logger_manager.log_error("Error clearing preview", e)

    def _compare_corrected_files(self):
        """Show the comparison preview of corrected files."""
        try:
            if not self._corrected_files:
                messagebox.showerror("❌ Error", "No corrected files available. Run correction first.")
                return
            
            self.show_corrected_preview(self._corrected_files)
            self._compare_btn.config(state='normal')
        except Exception as e:
            error_msg = "Error displaying comparison preview"
            self.logger_manager.log_error(error_msg, e)
            messagebox.showerror("❌ Error", f"Failed to show preview: {str(e)}")

    def _preview_update(self):
        """Render the current preview pair display."""
        # Prevent recursive calls from Configure events
        if self._preview_updating:
            return

        try:
            self._preview_updating = True

            # Clear preview area - destroy only non-header widgets
            children_to_destroy = [w for w in self._right_frame.winfo_children() if w != self._right_header]
            for widget in children_to_destroy:
                try:
                    widget.destroy()
                except:
                    pass

            # If there are no preview pairs, show a message and return
            if not self._preview_pairs or len(self._preview_pairs) == 0:
                message_frame = Frame(self._right_frame, bg=self.colors['bg_light'])
                message_frame.pack(fill=BOTH, expand=True, pady=20, padx=20)
                msg_label = Label(message_frame, 
                                 text="No preview available. Run correction and click 'Compare Corrected Files' to view before/after preview.", 
                                 bg=self.colors['bg_light'], fg=self.colors['warning'],
                                 font=('Arial', 11), justify='center')
                msg_label.pack(expand=True)
                return

            # Main vertical layout for preview area
            preview_container = Frame(self._right_frame, bg='#f0f0f0')
            preview_container.pack(fill=BOTH, expand=True, after=self._right_header)

            # Fixed footer bar for navigation buttons
            footer_bar = Frame(preview_container, bg='#e0e0e0', height=50, relief='raised', bd=1)
            footer_bar.pack(side=BOTTOM, fill=X)
            footer_bar.pack_propagate(False)

            nav_frame = Frame(footer_bar, bg='#e0e0e0')
            nav_frame.pack(side=LEFT, anchor='sw', pady=8, padx=8, fill=BOTH, expand=True)

            Button(nav_frame, text="First", width=8, command=lambda: self._preview_goto('first')).pack(side=LEFT, padx=2)
            Button(nav_frame, text="Previous", width=8, command=lambda: self._preview_goto('prev')).pack(side=LEFT, padx=2)
            Button(nav_frame, text="Next", width=8, command=lambda: self._preview_goto('next')).pack(side=LEFT, padx=2)
            Button(nav_frame, text="Last", width=8, command=lambda: self._preview_goto('last')).pack(side=LEFT, padx=2)

            idx_label = Label(nav_frame, text=f"Pair {self._preview_pair_idx+1} of {len(self._preview_pairs)}", bg='#e0e0e0', font=(None, 9, 'bold'))
            idx_label.pack(side=LEFT, padx=15)

            # Simple frame for preview content
            preview_main = Frame(preview_container, bg='#f0f0f0')
            preview_main.pack(fill=BOTH, expand=True)

            # Display current pair
            if self._preview_pair_idx >= len(self._preview_pairs):
                self._preview_pair_idx = 0

            pair = self._preview_pairs[self._preview_pair_idx]
            self._preview_thumbs = []

            # Calculate preview size
            preview_area = self._right_frame
            preview_area.update_idletasks()
            area_width = preview_area.winfo_width() or 800
            area_height = preview_area.winfo_height() or 600

            # Account for header and footer
            usable_height = max(200, (area_height - 120) // 2)
            usable_width = max(300, area_width - 20)

            margin = 10
            thumb_width = max(200, (usable_width - margin * 4) // 2)
            thumb_height = usable_height - 40  # Account for label
            thumb_size = (thumb_width, thumb_height)

            # Before pair
            before_label = Label(preview_main, text="Before", bg='#f0f0f0', fg='blue', font=(None, 12, 'bold'), anchor='w', justify='left')
            before_label.pack(fill=X, padx=margin, pady=(8, 4))

            before_row = Frame(preview_main, bg='#f0f0f0', relief='solid', borderwidth=1)
            before_row.pack(fill=BOTH, expand=True, padx=margin, pady=2)

            self._render_image_pair(before_row, pair[0], thumb_width, thumb_size, margin)

            # After pair
            after_label = Label(preview_main, text="After", bg='#f0f0f0', fg='green', font=(None, 12, 'bold'), anchor='w', justify='left')
            after_label.pack(fill=X, padx=margin, pady=(8, 4))

            after_row = Frame(preview_main, bg='#f0f0f0', relief='solid', borderwidth=1)
            after_row.pack(fill=BOTH, expand=True, padx=margin, pady=2)

            self._render_image_pair(after_row, pair[1], thumb_width, thumb_size, margin)

            # Store rendered size to prevent immediate redundant resize redraws.
            self._preview_last_size = (self._right_frame.winfo_width(), self._right_frame.winfo_height())

        except Exception as e:
            error_msg = "Error updating preview display"
            self.logger_manager.log_error(error_msg, e)
            return
        finally:
            self._preview_updating = False

    def _render_image_pair(self, parent_frame, filenames, thumb_width, thumb_size, margin):
        """Render a pair of images with filenames below.
        
        Args:
            parent_frame: Frame to render into
            filenames: List of two image filenames (one may be None)
            thumb_width: Width for thumbnail
            thumb_size: Size tuple for thumbnail (width, height)
            margin: Margin in pixels
        """
        for fname in filenames:
            col = Frame(parent_frame, bg='#f0f0f0')
            col.pack(side=LEFT, padx=margin//2, expand=True, fill=BOTH)
            
            if fname:
                try:
                    img_path = os.path.join(self.folder_path, fname)
                    img = ImageProcessor.load_and_resize_image(img_path)
                    if img:
                        img.thumbnail(thumb_size)
                        thumb = ImageTk.PhotoImage(img)
                        lbl = Label(col, image=thumb, bg='#f0f0f0', relief='solid', borderwidth=1)
                        lbl.pack(side=TOP, expand=True, fill=BOTH, padx=2, pady=2)
                        # Store filename for magnifier to find
                        lbl._image_filename = fname
                        # Bind directly on image labels so magnifier tracks cursor over preview images.
                        lbl.bind('<Motion>', self._on_magnifier_motion)
                        lbl.bind('<Leave>', self._hide_magnifier)
                        lbl.config(cursor='crosshair' if self._magnifier_active else 'arrow')
                        self._preview_thumbs.append(thumb)
                        name_lbl = Label(col, text=fname, bg='#f0f0f0', anchor='center', wraplength=thumb_width, font=(None, 7), fg='#666')
                        name_lbl.pack(side=TOP, fill=X, padx=2, pady=2)
                    else:
                        # Error loading image
                        error_lbl = Label(col, text=f"Error loading:\n{fname}", bg='#f0f0f0', fg='red', font=(None, 8), relief='solid', borderwidth=1)
                        error_lbl.pack(side=TOP, expand=True, fill=BOTH, padx=2, pady=2)
                except Exception as e:
                    self.logger_manager.log_error(f"Error rendering image {fname}", e)
                    error_lbl = Label(col, text=f"Error:\n{str(e)[:20]}", bg='#f0f0f0', fg='red', font=(None, 7), relief='solid', borderwidth=1)
                    error_lbl.pack(side=TOP, expand=True, fill=BOTH, padx=2, pady=2)
            else:
                # Empty placeholder
                empty_lbl = Label(col, text="(No image)", bg='#f0f0f0', fg='#999', font=(None, 8))
                empty_lbl.pack(side=TOP, expand=True, fill=BOTH, padx=2, pady=2)

    def _set_preview_image_cursor(self, cursor_style):
        """Set cursor style for all currently rendered preview image labels."""
        for widget in self._right_frame.winfo_children():
            self._set_cursor_recursive(widget, cursor_style)

    def _set_cursor_recursive(self, widget, cursor_style):
        """Recursively apply cursor style to preview image labels only."""
        try:
            if hasattr(widget, '_image_filename'):
                widget.config(cursor=cursor_style)
        except Exception:
            pass

        try:
            for child in widget.winfo_children():
                self._set_cursor_recursive(child, cursor_style)
        except Exception:
            pass

    def _preview_goto(self, where):
        """Navigate to a specific pair in the preview.
        
        Args:
            where: Navigation direction ('first', 'last', 'prev', 'next')
        """
        if where == 'first':
            self._preview_pair_idx = 0
        elif where == 'last':
            self._preview_pair_idx = len(self._preview_pairs) - 1
        elif where == 'prev':
            if self._preview_pair_idx > 0:
                self._preview_pair_idx -= 1
        elif where == 'next':
            if self._preview_pair_idx < len(self._preview_pairs) - 1:
                self._preview_pair_idx += 1
        self._preview_update()

    def reset(self):
        """Reset the application to initial state."""
        self.folder_path = ''
        self.image_files = []
        self._corrected_files = []
        self._preview_pairs = []
        self._preview_pair_idx = 0
        self._preview_last_size = (0, 0)
        if self._preview_resize_after_id:
            try:
                self.master.after_cancel(self._preview_resize_after_id)
            except Exception:
                pass
            self._preview_resize_after_id = None
        self.info_label.config(text="📁 No folder selected.")
        self.first_entry.delete(0, 'end')
        self.last_entry.delete(0, 'end')
        self.intermediate_label.config(text="Intermediate: 0 images", fg=self.colors['warning'])
        self.status_label.config(text="🟢 Ready", fg=self.colors['success'])
        self._compare_btn.config(state='disabled')
        if self._magnifier_active:
            self._toggle_magnifier()
        self._hide_magnifier(None)

        # Reset right preview section fully.
        children_to_destroy = [w for w in self._right_frame.winfo_children() if w != self._right_header]
        for widget in children_to_destroy:
            try:
                widget.destroy()
            except Exception:
                pass

        self.corrected_preview_label = Label(
            self._right_frame,
            text="Select folder and run correction to see preview.",
            bg=self.colors['bg_light'],
            fg=self.colors['text_secondary'],
            font=('Arial', 10)
        )
        self.corrected_preview_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        for lbl in self.thumb_labels:
            lbl.destroy()
        self.thumb_labels = []
        self.thumbnails = []
        self._selected_thumb_idx = None


class ImageViewer:
    """Standalone window for viewing individual images with navigation."""
    
    def __init__(self, master, folder_path, image_files, start_idx=0):
        """Initialize image viewer window.
        
        Args:
            master: Parent window
            folder_path: Path to folder containing images
            image_files: List of image filenames
            start_idx: Starting image index
        """
        self.folder_path = folder_path
        self.image_files = image_files
        self.current_idx = start_idx
        self.thumbnails = []  # Keep references to prevent garbage collection
        
        self.top = Toplevel(master)
        self.top.title("Image Viewer")
        
        self.label_text = Label(self.top, text="")
        self.label_text.pack()
        
        self.label = Label(self.top)
        self.label.pack()
        
        # Navigation buttons
        btn_frame = Frame(self.top)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="First", command=self.first_img).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Previous", command=self.prev_img).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Next", command=self.next_img).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Last", command=self.last_img).grid(row=0, column=3, padx=5)
        
        # Keyboard bindings
        self.top.bind('<Left>', self._on_key)
        self.top.bind('<Right>', self._on_key)
        self.top.bind('<Control-Left>', self._on_key)
        self.top.bind('<Control-Right>', self._on_key)
        
        self._show_image(self.current_idx)
    
    def _show_image(self, idx):
        """Display image at specified index."""
        img_path = os.path.join(self.folder_path, self.image_files[idx])
        img = ImageProcessor.load_and_resize_image(
            img_path,
            max_size=(int(self.top.winfo_screenwidth() * 0.8), int(self.top.winfo_screenheight() * 0.8))
        )
        
        if img:
            photo = ImageTk.PhotoImage(img)
            self.label.config(image=photo)
            self.label.image = photo
            self.thumbnails.append(photo)  # Keep reference
            self.label_text.config(text=f"{idx+1}/{len(self.image_files)}: {os.path.basename(img_path)}")
        else:
            self.label.config(image='')
            self.label.image = None
            self.label_text.config(text=f"Error loading image: {img_path}")
    
    def prev_img(self):
        """Show previous image."""
        if self.current_idx > 0:
            self.current_idx -= 1
            self._show_image(self.current_idx)
    
    def next_img(self):
        """Show next image."""
        if self.current_idx < len(self.image_files) - 1:
            self.current_idx += 1
            self._show_image(self.current_idx)
    
    def first_img(self):
        """Show first image."""
        self.current_idx = 0
        self._show_image(self.current_idx)
    
    def last_img(self):
        """Show last image."""
        self.current_idx = len(self.image_files) - 1
        self._show_image(self.current_idx)
    
    def _on_key(self, event):
        """Handle keyboard navigation."""
        if event.keysym == 'Left':
            if event.state & 0x4:  # Ctrl pressed
                self.first_img()
            else:
                self.prev_img()
        elif event.keysym == 'Right':
            if event.state & 0x4:  # Ctrl pressed
                self.last_img()
            else:
                self.next_img()


def main():
    """Application entry point with comprehensive error handling."""
    logger = logging.getLogger("ImageOrderToolLogger")
    try:
        root = Tk()
        logger.info("="*80)
        logger.info("Application started")
        logger.info("="*80)
        
        # Set window size to fit above the taskbar
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        # Reserve 80px for the taskbar (typical size)
        window_height = screen_height - 80
        window_width = int(screen_width * 0.95)
        root.geometry(f"{window_width}x{window_height}+0+0")
        
        app = ImageOrderTool(root)
        logger.info("GUI initialized successfully")
        
        root.mainloop()
        logger.info("Application closed normally")
        logger.info("="*80)
    except KeyboardInterrupt:
        logger.warning("Application interrupted by user (Ctrl+C)")
        logger.info("="*80)
    except Exception as e:
        crash_msg = f"Unhandled exception in main application loop: {type(e).__name__}: {str(e)}"
        logger.critical(crash_msg)
        logger.critical(f"Full traceback:\n{traceback.format_exc()}")
        logger.info("="*80)
        try:
            messagebox.showerror("❌ Critical Error", f"Application crashed: {str(e)}\n\nSee log file for details.")
        except:
            pass  # GUI might be unavailable


if __name__ == "__main__":
    main()

