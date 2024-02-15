import os
import sys
from litemapy.schematic import Schematic, Region, BlockState
import csv
import math
from tkinter import *
from tkinter import ttk, filedialog

CarpetMode = False


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def inputFileCheck():
    file = filedialog.askopenfile(mode='r', filetypes=[('Litematic Files', '*.litematic')])
    global filepath
    if file:
        filepath = os.path.abspath(file.name)
        root.destroy()


def window():
    global root
    root = Tk()
    frm = ttk.Frame(root, padding=30)
    frm.grid()
    winWidth = root.winfo_reqwidth()
    winwHeight = root.winfo_reqheight()
    posRight = int(root.winfo_screenwidth() / 2 - winWidth / 2)
    posDown = int(root.winfo_screenheight() / 2 - winwHeight / 2)
    root.geometry("+{}+{}".format(posRight, posDown))
    ttk.Button(frm, text="Browse", command=inputFileCheck).grid(column=0, row=0)
    root.mainloop()


window()
from PIL import Image, ImageFont, ImageDraw
# this seems to be conflicting with  tkinter for some reason, no idea why

# pixel coords of images and loading images and font
text_coords = (8, 6)
first_item_coords = (8, 18)
spacing = 18
inventory = Image.open(resource_path('shulker_box.png')).convert('RGBA')
shovel = Image.open(resource_path('wooden_shovel.png')).convert('RGBA')
water_potion = Image.open(resource_path('water_potion.png')).convert('RGBA')
font = ImageFont.truetype(resource_path(f'Minecraft Regular.otf'), 10)


def make_box_preview(sequence, name, file_path):
    new_box = inventory.copy()
    for slot_number, item in enumerate(sequence):
        slot_coords = ((slot_number % 9) * 18 + first_item_coords[0], (slot_number % 27 // 9) * 18 + first_item_coords[1])

        if item == '1':  # puts items in shulker
            new_box.paste(water_potion, slot_coords, water_potion)
        else:
            new_box.paste(shovel, slot_coords, shovel)

    # add text and save image
    draw = ImageDraw.Draw(new_box)
    draw.text(text_coords, name, font=font, fill=(63, 63, 63))
    new_box.save(file_path + '/' + name + '.png')


pattern_name = os.path.basename(filepath).removesuffix('.litematic')
schematic_folder = resource_path('assets')
pattern_region = list(Schematic.load(filepath).regions.values())[0]
output_folder = os.path.join(os.path.dirname(filepath), f"{pattern_name} files")
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# check how many block types there are, assign each one a binary code and create a schematic with said mapping
block_types = {}
# {block type: count}
for x in pattern_region.xrange():
    for z in pattern_region.zrange():
        blocks = []
        for y in pattern_region.yrange():
            blocks.append(pattern_region.getblock(x, y, z).blockid)
            # check if there are any air blocks on top or gravity blocks requiring a different end module
            if CarpetMode is False:
                if y == pattern_region.height - 1 and pattern_region.getblock(x, y, z).blockid == 'minecraft:air':
                    CarpetMode = True
                else:
                    for check in 'carpet', 'powder', 'sand', 'gravel':
                        if check in pattern_region.getblock(x, y, z).blockid:
                            CarpetMode = True

        blocks = ' '.join(blocks)
        if blocks not in block_types:
            block_types[blocks] = 1
        else:
            block_types[blocks] += 1

mapping = Region(0, 0, 0, len(block_types), pattern_region.height, 1)
for x, key in enumerate(block_types):
    for y, block in enumerate(list(block_types.keys())[x].split()):
        mapping.setblock(x, y, 0, BlockState(block))

mapping.as_schematic(f'{pattern_name}_mapping').save(f'{output_folder}/{pattern_name}_mapping.litematic')

# create a csv file with the required resources per slot per tile
with open(f'{output_folder}/{pattern_name} resources.csv', 'w', newline='') as resources_csv:
    fieldnames = [f"layer {n + 1}" for n in pattern_region.yrange()] + ['amount']
    writer = csv.DictWriter(resources_csv, fieldnames=fieldnames)
    writer.writeheader()

    for block_type in block_types:
        block_type_list = block_type.split('minecraft:')
        row = {f'layer {n + 1}': block_type_list[n + 1] for n in pattern_region.yrange()}
        row['amount'] = block_types[block_type]
        writer.writerow(row)

resources_csv.close()

blocktype_bit_span = math.ceil(math.log(len(block_types), 2))  # coding is my passion
block_types = {block_type: list(format(n + 1, f"0{blocktype_bit_span}b"))[::-1] for n, block_type in
               enumerate(list(block_types.keys()))}
# {block_type: number}

"""
mapping out any exploitable repetition
"""

# mapping the repetition and generating the sequence for the storage based ROM
repetition = {}

for x in pattern_region.xrange():
    row = []
    for z in pattern_region.zrange():
        row.append(''.join([(pattern_region.getblock(x, y, z)).blockid for y in pattern_region.yrange()]))
    row = ''.join(row)

    if row not in repetition:
        repetition[row] = [x]
    else:
        repetition[row].append(x)

repetition = [repetition[key] for key in repetition.keys()]

# check for Z axis symmetry
x_symmetry = True
for x in pattern_region.xrange():
    row = []
    for z in pattern_region.zrange():
        row.append(''.join([(pattern_region.getblock(x, y, z)).blockid for y in pattern_region.yrange()]))

    if row != row[::-1]:
        x_symmetry = False

"""
creating a blank memory cell and stacking it vertically
"""
vert_bit_span = math.ceil(math.log2(len(repetition)))  # coding is truly my passion
assert vert_bit_span <= 5, f'pattern too large, vertical bits: {vert_bit_span}'

# loading in the schematics
if x_symmetry:

    memory_length = math.ceil(pattern_region.length / 2)

    start = list(Schematic.load(f'{schematic_folder}/start with symmetry.litematic').regions.values())[0]
    module = list(Schematic.load(f'{schematic_folder}/module with symmetry.litematic').regions.values())[0]
    repeater = list(Schematic.load(f'{schematic_folder}/repeater with symmetry.litematic').regions.values())[0]
    end = list(Schematic.load(f'{schematic_folder}/end with symmetry.litematic').regions.values())[0]

    memory_region = Region(0, 0, 0, memory_length + ((memory_length - 1) // 9) + 5, (4 * len(repetition)) + 2,
                           blocktype_bit_span + 6)
else:

    memory_length = pattern_region.length

    start = list(Schematic.load(f'{schematic_folder}/start no symmetry.litematic').regions.values())[0]
    module = list(Schematic.load(f'{schematic_folder}/module no symmetry.litematic').regions.values())[0]
    repeater = list(Schematic.load(f'{schematic_folder}/repeater no symmetry.litematic').regions.values())[0]

    memory_region = Region(0, 0, 0, memory_length + ((memory_length - 1) // 9) + 3, (4 * len(repetition)) + 2,
                           blocktype_bit_span + 6)

for memory_module in range(len(repetition)):
    for x, y, z in start.allblockpos():
        if start.getblock(x, y, z).blockid != 'minecraft:air':
            memory_region.setblock(x, (4 * memory_module) + y, z, start.getblock(x, y, z))

    offset = 4
    for i in range(memory_length - 1):
        if (i + 1) % 9 != 0:
            for x, y, z in module.allblockpos():
                if module.getblock(x, y, z).blockid != 'minecraft:air':
                    memory_region.setblock(offset, (4 * memory_module) + y, z, module.getblock(x, y, z))
            offset += 1

        else:
            for x, y, z in repeater.allblockpos():
                if repeater.getblock(x, y, z).blockid != 'minecraft:air':
                    memory_region.setblock(offset + x, (4 * memory_module) + y, z, repeater.getblock(x, y, z))
            offset += 2

    if x_symmetry:
        for x, y, z in end.allblockpos():
            if end.getblock(x, y, z).blockid != 'minecraft:air':
                memory_region.setblock(offset + x - 1, (4 * memory_module) + y, z, end.getblock(x, y, z))
            if pattern_region.length % 2 == 1:
                memory_region.setblock(offset - 1, (4 * memory_module) + 3, 2, BlockState('minecraft:air'))

    for i in range(blocktype_bit_span - 1):
        for x in memory_region.xrange():
            for y in range(6):
                if memory_region.getblock(x, y, 5).blockid != 'minecraft:air':
                    memory_region.setblock(x, (4 * memory_module) + y, i + 6, memory_region.getblock(x, y, 5))

    for y in range(6):
        memory_region.setblock(0, (4 * memory_module) + y, 5 + blocktype_bit_span, BlockState('minecraft:moss_block'))

"""
encoding the blank memory modules
"""

for x_pattern, layer in enumerate([repetition[i][0] for i in range(len(repetition))]):
    for block in range((math.ceil(pattern_region.length / 2) if x_symmetry else pattern_region.length)):
        block_type = ' '.join([pattern_region.getblock(layer, y, block).blockid for y in pattern_region.yrange()])
        for bit, value in enumerate(block_types[block_type]):
            if value == '1':
                memory_region.setblock(3 + block + (block // 9), 4 + (4 * x_pattern), 5 + bit,
                                       BlockState('minecraft:observer', {'facing': 'down'}))

"""
adding the vertical wiring
"""
wire_region = list(Schematic.load(f'{schematic_folder}/vertical wire.litematic').regions.values())[0]
wire_top_region = list(Schematic.load(f'{schematic_folder}/vertical wire top.litematic').regions.values())[0]
for y in memory_region.yrange()[:-5]:
    for x in wire_region.xrange():
        memory_region.setblock(x, y, 1, wire_region.getblock(x, y % wire_region.height, 0))

for y in memory_region.yrange()[-5:-2]:
    for x in wire_top_region.xrange():
        memory_region.setblock(x, y, 1, wire_top_region.getblock(x, y - memory_region.height + 5, 0))

regions = {f'{pattern_name} memory': memory_region}

reset_wire_region = Region(-2, 0, 4, wire_region.width, memory_region.height - 2, wire_region.length)
for x, y, z in reset_wire_region.allblockpos():
    reset_wire_region.setblock(x, y, z, memory_region.getblock(x, y, z + 1))
regions['reset wire'] = reset_wire_region

"""
adding the vertical decoder
"""
assert blocktype_bit_span <= 5, f'too many block types, try encoding fewer layers or optimising the pattern, bits:{blocktype_bit_span}'

if vert_bit_span == 4:
    vert_dec_region = \
        list(Schematic.load(f'{schematic_folder}/4bit vertical decoder.litematic').regions.values())[0]
    vert_decoder_top = \
        list(Schematic.load(f'{schematic_folder}/4bit vertical decoder top.litematic').regions.values())[0]
    extra_bit = \
        list(Schematic.load(
            f'{schematic_folder}/4bit vertical decoder top extra.litematic').regions.values())[
            0]

else:
    vert_dec_region = \
        list(Schematic.load(f'{schematic_folder}/5bit vertical decoder {4 if blocktype_bit_span <= 4 else 5}bit.litematic').regions.values())[0]
    vert_decoder_top = \
        list(Schematic.load(f'{schematic_folder}/5bit vertical decoder top.litematic').regions.values())[0]
    extra_bit = \
        list(Schematic.load(
            f'{schematic_folder}/5bit vertical decoder top extra.litematic').regions.values())[0]

vert_decoder = Region(2, -1, -2, vert_dec_region.width, (4 * len(repetition)) + 3, vert_dec_region.length)

for x in vert_decoder.xrange():
    for y in vert_decoder.yrange()[:-4]:
        for z in vert_decoder.zrange():
            vert_decoder.setblock(x, y, z, vert_dec_region.getblock(x, y, z))

z_decoder = 0 if ((len(repetition) - 1) % 6) >= 3 else 1

for x, y, z in vert_decoder_top.allblockpos():
    if vert_decoder_top.getblock(x, y, z).blockid != 'minecraft:air':
        vert_decoder.setblock(x, y + (4 * len(repetition)) - 2, z + z_decoder, vert_decoder_top.getblock(x, y, z))

if len(repetition) % 3 == 1:
    for x, y, z in extra_bit.allblockpos():
        vert_decoder.setblock(x, vert_decoder.height - 4 + y, 1 if z_decoder == 0 else 0, extra_bit.getblock(x, y, z))

regions['vertical decoder'] = vert_decoder

"""
pasting in the main section
"""
blocktype_bit_span = 4 if blocktype_bit_span <= 4 else 5
x_offset, y_offset, z_offset = (4, -12, -2) if blocktype_bit_span == 4 else (5, -11, -2)
main_bit = Schematic.load(f'{schematic_folder}/{blocktype_bit_span}bit main part.litematic').regions
for key in main_bit.keys():
    subregion = main_bit[key]
    new_subregion = Region(subregion.x + x_offset, subregion.y + y_offset, subregion.z + z_offset, subregion.width,
                           subregion.height, subregion.length)
    for x, y, z in subregion.allblockpos():
        new_subregion.setblock(x, y, z, subregion.getblock(x, y, z))
    regions[key] = new_subregion

"""
pasting in the storage based rom
"""

storage_rom = Schematic.load(f'{schematic_folder}/{vert_bit_span}bit_vert {blocktype_bit_span}bit_blocktypes decoder + rom connection.litematic').regions
extra_offset = -1 if vert_bit_span == 5 else 0
for key in storage_rom.keys():
    subregion = storage_rom[key]
    new_subregion = Region(subregion.x + 5, subregion.y - 8 + extra_offset,
                           subregion.z - 14 - (1 if blocktype_bit_span == 5 else 0),
                           subregion.width,
                           subregion.height, subregion.length)
    for x, y, z in subregion.allblockpos():
        new_subregion.setblock(x, y, z, subregion.getblock(x, y, z))
    regions[key] = new_subregion

"""
adding the dropper line
"""
x_offset, z_offset = (15, -1) if blocktype_bit_span == 5 else (0, 0)
length = pattern_region.length - (7 if CarpetMode else 5)

dl_module = list(Schematic.load(f'{schematic_folder}/dropper line module.litematic').regions.values())[0]
dl_repeater = list(Schematic.load(f'{schematic_folder}/dropper line repeater.litematic').regions.values())[0]
dropper_line = Region(26 + x_offset, -15, -5 + z_offset, length, dl_repeater.height, dl_repeater.length)

lines_done = 0
rail_power = -5

while lines_done < length:
    if rail_power != -5 or lines_done >= length - 5:
        for x, y, z in dl_module.allblockpos():
            dropper_line.setblock(lines_done, y, z, dl_module.getblock(x, y, z))
        lines_done += 1
        rail_power -= 1
    else:
        for x, y, z in dl_repeater.allblockpos():
            dropper_line.setblock(lines_done + x, y, z, dl_repeater.getblock(x, y, z))
        lines_done += 5
        rail_power = 7

if rail_power < 2:
    for x, y, z in dl_repeater.allblockpos():
        dropper_line.setblock(lines_done + x - 5, y, z, dl_repeater.getblock(x, y, z))
regions[f'dropper line'] = dropper_line

"""
adding the end of the dropper line
"""
if CarpetMode:
    dropper_line_end_schematic = list(Schematic.load(f'{schematic_folder}/carpet compat end module.litematic').regions.values())[0]
    offsets = (0, -14, 0)
else:
    dropper_line_end_schematic = list(Schematic.load(f'{schematic_folder}/dropper line end.litematic').regions.values())[0]
    offsets = (0, -2, 11)

dropper_line_end = Region(dropper_line.x + length + offsets[0], dropper_line.y + offsets[1],
                          dropper_line.z + offsets[2], dropper_line_end_schematic.width,
                          dropper_line_end_schematic.height, dropper_line_end_schematic.length)

for x, y, z in dropper_line_end_schematic.allblockpos():
    dropper_line_end.setblock(x, y, z, dropper_line_end_schematic.getblock(x, y, z))
regions['dropper line end'] = dropper_line_end

Schematic(f'{pattern_name} printer', regions=regions).save(f'{output_folder}/{pattern_name} printer.litematic')

"""
generate the sequence that needs to be encoded into the storage based rom
"""

rom_sequence = {repetition[i][j]: i for i in range(len(repetition)) for j in range(len(repetition[i]))}
rom_sequence = [rom_sequence[i] for i in range(len(rom_sequence))]
rom_sequence = [format(n, f"0{vert_bit_span}b") for n in rom_sequence]

if not os.path.exists(f"{output_folder}/storage based ROM encoding"):
    os.makedirs(f"{output_folder}/storage based ROM encoding")

for rom_bit in range(vert_bit_span):
    bit_sequence = ''.join([n[-(rom_bit + 1)] for n in rom_sequence])
    boxes = []
    box = []
    for index, bit in enumerate(bit_sequence):
        box.append(bit)
        if (index + 1) % 27 == 0:
            boxes.append(''.join(box))
            box = []
    if (index + 1) % 27 != 0:
        boxes.append(''.join(box))
    if len(boxes[-1]) < 4:
        boxes[-1] = boxes[-2][-3:] + boxes[-1]
        boxes[-2] = boxes[-2][:-3]
    if len(boxes) == 1:
        boxes.append(boxes[0])
    for index, box in enumerate(boxes):
        make_box_preview(box, f"{rom_bit + 1}.{index + 1}", f"{output_folder}/storage based ROM encoding")
