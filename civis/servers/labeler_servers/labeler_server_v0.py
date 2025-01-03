import numpy as np
import pandas as pd
from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource, Slider, Button, TextInput, Spacer, Div, Select, TapTool, Tabs, \
    TabPanel
from bokeh.layouts import column, row
import json
import h5py
import os
import sys
from pathlib import Path

# Set up paths similar to place finder server
current_dir = os.path.dirname(os.path.abspath(__file__))
servers_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(servers_dir)
sys.path.append(project_root)

CONFIG_PATH = os.path.join(project_root, 'config.json')


def load_data(filename):
    """
    Load all data
    :param filename: .mat file containing config, spatial, Cn, Coor, ids, etc...
    :return: essential variables for plotting
    """
    with h5py.File(filename, 'r') as file:
        data = file['data']
        Cn = np.transpose(data['Cn'][()])
        ids = data['ids'][()] - 1
        Coor_cell_array = data['Coor']
        Coor = []
        C_raw = np.transpose(data['C_raw'][()])
        C = np.transpose(data['C'][()])
        C_denoised = np.transpose(data['C_denoised'][()])
        C_deconvolved = np.transpose(data['C_deconvolved'][()])
        C_reraw = np.transpose(data['C_reraw'][()])
        centroids = np.transpose(data['centroids'][()])
        virmenPath = data['virmenPath'][()].tobytes().decode('utf-16le')

        for i in range(Coor_cell_array.shape[1]):
            ref = Coor_cell_array[0, i]  # Get the reference
            coor_data = file[ref]  # Use the reference to access the data
            coor_matrix = np.array(coor_data)  # Convert to a NumPy array

            Coor.append(np.transpose(coor_matrix))

    return C, C_raw, Cn, ids, Coor, centroids, virmenPath, C_denoised, C_deconvolved, C_reraw


def labeler_bkapp_v0(doc):
    global C, C_raw, ids, labels, image_source, session_name, C_denoised, C_deconvolved, C_reraw
    filename = ''
    labels = np.zeros((3, 3), dtype=bool)
    labels[:, 2] = True

    """
    ========================================================================================================================
            Bokeh Setup
    ========================================================================================================================
    """

    custom_bright_colors = [
        '#e6194B',  # Bright Red
        '#3cb44b',  # Bright Green
        '#ffe119',  # Bright Yellow
        '#4363d8',  # Bright Blue
        '#f58231',  # Bright Orange
        '#911eb4',  # Bright Purple
        '#42d4f4',  # Bright Cyan
        '#f032e6',  # Bright Magenta
        '#bfef45',  # Bright Lime
        '#fabed4',  # Light Pink
        '#469990',  # Teal
        '#dcbeff',  # Lavender
        '#9A6324',  # Brown
        '#fffac8',  # Beige
        '#800000',  # Maroon
        '#aaffc3',  # Mint
        '#808000',  # Olive
        '#ffd8b1',  # Coral
        '#000075',  # Navy
    ]

    spatial_source = ColumnDataSource(data={
        'xs': [],
        'ys': [],
        'id': [],
        'colors': [],
    })

    temporal_source = ColumnDataSource(data={'x': [],
                                             'y_lowpass': [],
                                             'y_raw': [],
                                             'y_denoised': [],
                                             'y_deconvolved': [],
                                             'y_reraw': []
                                             })

    image_source = ColumnDataSource(data={'image': []})

    TOOLS = "crosshair,pan,wheel_zoom,zoom_in,zoom_out,box_zoom,undo,redo,reset,save,box_select,poly_select,lasso_select,examine,help"

    # spatial image
    spatial = figure(title="Neuronal Segmentation", width=800, height=800,
                     active_scroll='wheel_zoom', tools=TOOLS)
    spatial.image(image='image', x=0, y=0, dw=100, dh=100, source=image_source)

    contour_renderer = spatial.patches(xs='xs', ys='ys', source=spatial_source,
                                       fill_alpha=0.4, fill_color='colors', line_color='colors')

    hover = HoverTool(tooltips=[("ID", "@id")], renderers=[contour_renderer])
    spatial.add_tools(hover)
    taptool = TapTool(mode='replace')
    spatial.add_tools(taptool)

    # temporal1 transient
    temporal1 = figure(title="Temporal Activity", width=800, height=400, active_scroll="wheel_zoom")
    temporal1.line('x', 'y_lowpass', source=temporal_source, line_width=2, color="red", legend_label="Lowpass")
    temporal1.line('x', 'y_raw', source=temporal_source, line_width=2, color="blue", legend_label="Raw")
    temporal1.legend.click_policy = "hide"
    temporal_tab1 = TabPanel(child=temporal1, title="Raw")

    # temporal2 transient
    temporal2 = figure(title="Temporal Activity", width=800, height=400, x_range=temporal1.x_range,
                       active_scroll="wheel_zoom")
    temporal2.line('x', 'y_deconvolved', source=temporal_source, line_width=2, color="green", alpha=0.7,
                   legend_label="Deconvolved")
    temporal2.line('x', 'y_denoised', source=temporal_source, line_width=2, color="red", alpha=0.7,
                   legend_label="Denoised")
    temporal2.line('x', 'y_reraw', source=temporal_source, line_width=2, color='blue', alpha=0.7, legend_label="Reraw")
    temporal2.legend.click_policy = "hide"
    temporal_tab2 = TabPanel(child=temporal2, title="Rebased")

    # Callback function to print the ID of the selected neuron
    def update_temporal(attr, old, new):
        # 'new' is directly the list of selected indices
        if new:
            selected_index = new[0]  # Get the index of the first selected neuron
            neuron_id = int(spatial_source.data['id'][selected_index][0])
            new_y_lowpass = C[neuron_id]
            new_y_raw = C_raw[neuron_id]
            new_y_denoised = C_denoised[neuron_id]
            new_y_deconvolved = C_deconvolved[neuron_id]
            new_y_reraw = C_reraw[neuron_id]
            new_x = np.arange(0, len(C[neuron_id]) / 20, 0.05)

            temporal_source.data = {
                'x': new_x,
                'y_lowpass': new_y_lowpass,
                'y_raw': new_y_raw,
                'y_denoised': new_y_denoised,
                'y_deconvolved': new_y_deconvolved,
                'y_reraw': new_y_reraw
            }

            temporal1.title.text = f"Temporal Activity: Neuron {neuron_id}"
            temporal2.title.text = f"Temporal Activity: Neuron {neuron_id}"
            neuron_id_slider.value = selected_index

    spatial_source.selected.on_change('indices', update_temporal)

    """
    ========================================================================================================================
            Add Slider to Bokeh layout
    ========================================================================================================================
    """
    neuron_id_slider = Slider(start=0, end=100, value=0, step=1, width=600, title="Neuron ID", disabled=True)

    def update_from_slider(attr, old, new):
        neuron_id = new  # Adjust for zero indexing; slider value starts from 1

        # Update the temporal1 plot
        new_y_lowpass = C[neuron_id]
        new_y_raw = C_raw[neuron_id]
        new_y_denoised = C_denoised[neuron_id]
        new_y_deconvolved = C_deconvolved[neuron_id]
        new_y_reraw = C_reraw[neuron_id]

        new_x = np.arange(0, len(C[neuron_id]) / 20, 0.05)
        temporal_source.data = {
            'x': new_x,
            'y_lowpass': new_y_lowpass,
            'y_raw': new_y_raw,
            'y_denoised': new_y_denoised,
            'y_deconvolved': new_y_deconvolved,
            'y_reraw': new_y_reraw
        }
        temporal1.title.text = f"Temporal Activity: Neuron {neuron_id}"  # Adjust text to match ID
        temporal2.title.text = f"Temporal Activity: Neuron {neuron_id}"  # Adjust text to match ID

        # Highlight the selected neuron in the spatial plot
        spatial_source.selected.indices = [neuron_id]
        neuron_index_input.value = str(neuron_id)
        update_button_styles()

    neuron_id_slider.on_change('value', update_from_slider)

    """
    ========================================================================================================================
            Add Buttons to Bokeh layout
    ========================================================================================================================
    """
    # Create "Previous" and "Next" buttons
    previous_button = Button(label="<<Previous", button_type="primary", disabled=True)
    next_button = Button(label="Next>>", button_type="primary", disabled=True)

    # Callback function for the "Previous" button
    def go_previous():
        current_value = neuron_id_slider.value
        if current_value > np.min(ids):
            neuron_id_slider.value = current_value - 1
            neuron_index_input.value = str(current_value - 1)

    # Callback function for the "Next" button
    def go_next():
        current_value = neuron_id_slider.value
        if current_value < np.max(ids):
            neuron_id_slider.value = current_value + 1
            neuron_index_input.value = str(current_value + 1)

    # Attach the callback functions to the buttons
    previous_button.on_click(go_previous)
    next_button.on_click(go_next)

    """
    ========================================================================================================================
            Add TextInput to Bokeh layout
    ========================================================================================================================
    """
    # Create a TextInput widget for neuron index input
    neuron_index_input = TextInput(value=str(neuron_id_slider.value), title="Neuron Index:", disabled=True)

    # Callback function for the TextInput to update the neuron index
    def update_index(attr, old, new):
        try:
            new_index = int(new)
            # Ensure the new index is within the valid range
            if np.min(ids) <= new_index <= np.max(ids):
                neuron_id_slider.value = new_index
            else:
                print("Input index out of range")
        except ValueError:
            print("Invalid input. Please enter a valid integer.")

    # Attach the callback function to the TextInput widget
    neuron_index_input.on_change('value', update_index)
    """
    ========================================================================================================================
            Labeling Widgets
    ========================================================================================================================
    """
    # Create buttons for labeling
    keep_button = Button(label="Keep", button_type="default", disabled=True)
    discard_button = Button(label="Discard", button_type="default", disabled=True)
    unlabeled_button = Button(label="Unlabeled", button_type="default", disabled=True)

    # Create a button for saving labels and a TextInput for the file path
    save_labels_button = Button(label="Save Labels", button_type="success", disabled=True)
    file_path_input = TextInput(value="labels.csv", title="File Path:", disabled=True)

    # Function to update labels based on button click
    def update_labels(new_label):
        selected_neuron = neuron_id_slider.value  # Adjust for indexing if necessary
        labels[selected_neuron] = [new_label == "Keep", new_label == "Discard", new_label == "Unlabeled"]
        update_button_styles()
        update_labeled_count()
        update_dropdowns()

    def save_labels():

        with open(CONFIG_PATH, 'r') as file:
            config = json.load(file)

        df = pd.DataFrame(labels, columns=["Keep", "Discard", "Unlabeled"])
        label_file_name = config['LabelsPath'] + session_name + '/' + session_name + '_' + file_path_input.value
        df.to_csv(label_file_name, index=False)
        print("Labels saved to", label_file_name)

    # Callbacks for buttons
    keep_button.on_click(lambda: update_labels("Keep"))
    discard_button.on_click(lambda: update_labels("Discard"))
    unlabeled_button.on_click(lambda: update_labels("Unlabeled"))
    save_labels_button.on_click(lambda: save_labels())

    # Function to update button styles based on current label
    def update_button_styles():
        selected_neuron = neuron_id_slider.value  # Adjust for indexing if necessary
        current_label = labels[selected_neuron]
        for button, label in zip([keep_button, discard_button, unlabeled_button], current_label):
            button.button_type = "success" if label else "default"

    # Initial update to set button styles
    update_button_styles()

    """
    ========================================================================================================================
            Div Plain Text Bokeh
    ========================================================================================================================
    """
    labeled_count_div = Div(text="Save: 0 | Discard: 0 | Unlabeled: 0", width=400, height=30)

    # Function to update the counts displayed in the Div
    def update_labeled_count():
        save_count = np.sum(labels[:, 0])
        discard_count = np.sum(labels[:, 1])
        unlabeled_count = np.sum(labels[:, 2])
        labeled_count_div.text = f"Save: {save_count} | Discard: {discard_count} | Unlabeled: {unlabeled_count}"

    # Initial update to set label div
    update_labeled_count()

    """
    ========================================================================================================================
            Add Select Menus to Bokeh layout
    ========================================================================================================================
    """
    kept_neurons_select = Select(title="Kept Neurons", options=[], disabled=True)
    discarded_neurons_select = Select(title="Discarded Neurons", options=[], disabled=True)
    unlabeled_neurons_select = Select(title="Unlabeled Neurons", options=[], disabled=True)

    def update_dropdowns():
        kept_ids = [str(i) for i, label in enumerate(labels) if label[0]]
        discarded_ids = [str(i) for i, label in enumerate(labels) if label[1]]
        unlabeled_ids = [str(i) for i, label in enumerate(labels) if label[2]]

        kept_neurons_select.options = ["Click to see options..."] + kept_ids
        discarded_neurons_select.options = ["Click to see options..."] + discarded_ids
        unlabeled_neurons_select.options = ["Click to see options..."] + unlabeled_ids

    # Initial update to set menu
    update_dropdowns()

    def neuron_selected(attr, old, new):
        # Ignore the placeholder selection
        if new == "Click to see options...":
            return

        selected_neuron_index = int(new)
        neuron_id_slider.value = selected_neuron_index

    # Attach the callback to all three select widgets
    kept_neurons_select.on_change('value', neuron_selected)
    discarded_neurons_select.on_change('value', neuron_selected)
    unlabeled_neurons_select.on_change('value', neuron_selected)

    """
    ========================================================================================================================
            Add Widgets to Update Loaded File
    ========================================================================================================================
    """

    # Filename input
    sessionname_input = TextInput(value=filename, title="SessionName:", width=400)
    load_data_button = Button(label="Load Data", button_type="success")

    def load_and_update_data(filename):
        global C, C_raw, ids, labels, image_source, C_denoised, C_deconvolved, C_reraw
        neuron_id_slider.disabled = False
        neuron_index_input.disabled = False
        next_button.disabled = False
        previous_button.disabled = False
        unlabeled_button.disabled = False
        keep_button.disabled = False
        save_labels_button.disabled = False
        discard_button.disabled = False
        unlabeled_neurons_select.disabled = False
        kept_neurons_select.disabled = False
        discarded_neurons_select.disabled = False
        file_path_input.disabled = False

        # Load the data
        [C, C_raw, Cn, ids, Coor, centroids, virmenPath, C_denoised, C_deconvolved, C_reraw] = load_data(filename)
        num_shapes = len(Coor)
        height, width = Cn.shape[:2]
        labels = np.zeros((len(C), 3), dtype=bool)
        labels[:, 2] = True

        # Prepare data for Bokeh
        x_positions_all = []
        y_positions_all = []

        for i in range(num_shapes):
            x_positions = Coor[i][0]
            y_positions = Coor[i][1]

            # Close the shape by ensuring the first point is repeated at the end
            x_positions_all.append(x_positions)
            y_positions_all.append(y_positions)

        y_positions_all = [[height - y for y in y_list] for y_list in y_positions_all]

        colors = [custom_bright_colors[i % len(custom_bright_colors)] for i in range(num_shapes)]

        # Update spatial_source with new data
        spatial_source.data = {
            'xs': x_positions_all,
            'ys': y_positions_all,
            'id': ids,
            'colors': [colors[i % len(colors)] for i in range(num_shapes)],  # Re-use or update colors as needed
        }

        # Update temporal_source with data from the first neuron as a default view
        temporal_source.data = {
            'x': np.arange(0, len(C[0]) / 20, 0.05),
            'y_lowpass': C[0],
            'y_raw': C_raw[0],
            'y_denoised': C_denoised[0],
            'y_deconvolved': C_deconvolved[0],
            'y_reraw': C_reraw[0]
        }

        # Reset or update additional widgets and plot properties
        neuron_id_slider.start = np.min(ids)
        neuron_id_slider.end = np.max(ids)
        neuron_id_slider.value = 0  # Reset to first neuron
        neuron_index_input.value = '0'  # Reset input box to first neuron
        update_button_styles()  # Call function to reset button styles if defined
        update_labeled_count()  # Reset label counts
        update_dropdowns()  # Update dropdown menus for labels

        # Update images and titles as needed
        image_source.data = {'image': [np.flipud(Cn)]}
        spatial.image(image='image', x=0, y=0, dw=width, dh=height, source=image_source)
        spatial.x_range.start = 0
        spatial.x_range.end = width
        spatial.y_range.start = 0
        spatial.y_range.end = height
        contour_renderer = spatial.patches(xs='xs', ys='ys', source=spatial_source,
                                           fill_alpha=0.4, fill_color='colors', line_color='colors')

        spatial.title.text = "Neuronal Segmentation"
        temporal1.title.text = "Temporal Activity: Neuron 0"
        temporal2.title.text = "Temporal Activity: Neuron 0"

        # Ensure the plots and UI components are updated correctly
        doc.title = f"Data Loaded: {filename}"  # Update document title with new filename

    # Callback function for the "Load Data" button to reload and update the visualization
    def update_data():
        global session_name

        with open(CONFIG_PATH, 'r') as file:
            config = json.load(file)
        session_name = sessionname_input.value
        neuron_path = os.path.join(config['ProcessedFilePath'], session_name, f'{session_name}_v7.mat')
        load_and_update_data(neuron_path)
        print(f"{neuron_path} loaded!")

    load_data_button.on_click(update_data)

    """
    ========================================================================================================================
            Setup Bokeh layout
    ========================================================================================================================
    """
    spacer1 = Spacer(height=50)
    spacer2 = Spacer(height=20)
    spacer3 = Spacer(width=20)

    choose_file = row(spacer3, sessionname_input, column(spacer2, load_data_button))

    controls = row(spacer3, column(spacer1, row(previous_button, next_button, neuron_index_input), neuron_id_slider))

    labelling = row(spacer3, column(
        row(keep_button, discard_button, unlabeled_button),
        row(file_path_input, column(spacer2, save_labels_button)),
        labeled_count_div))

    menus = row(spacer3, row(kept_neurons_select, discarded_neurons_select, unlabeled_neurons_select))

    temporal = Tabs(tabs=[temporal_tab1, temporal_tab2])

    layout = row(spatial, column(choose_file, controls, temporal, labelling, menus))

    doc.add_root(layout)

# bp = Blueprint("labeler", __name__, url_prefix='/labeler')
#
#
# @bp.route("/", methods=['GET'])
# def bkapp_page():
#     script = server_document("http://localhost:5006/labeler_bkapp")
#     return render_template("labeler.html", script=script, template="Flask", port=8000)
