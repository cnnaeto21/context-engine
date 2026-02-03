"""
Create Test Image for Dolphin Pipeline Verification

Generates a simple blueprint-style image with a construction asset table.
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path


def create_test_blueprint_image(output_path: Path):
    """
    Create a test blueprint image with an asset schedule table.

    Args:
        output_path: Path where image will be saved
    """
    # Create a white canvas (simulating blueprint)
    width, height = 1200, 800
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)

    # Use default font (larger size)
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        # Fallback to default font
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw title
    title = "CONSTRUCTION ASSET SCHEDULE - FLOOR 2"
    draw.text((50, 30), title, fill='black', font=font_large)

    # Draw project info
    draw.text((50, 80), "Project: Office Building Renovation", fill='black', font=font_small)
    draw.text((50, 110), "Revision: B | Date: 2024-02-15", fill='black', font=font_small)

    # Draw table
    table_x = 100
    table_y = 180
    col_widths = [150, 120, 140, 100, 80, 120]
    row_height = 50

    # Table headers
    headers = ["Asset ID", "Type", "Material", "Quantity", "Unit", "Cost"]

    # Table data
    data_rows = [
        ["Wall_A", "Wall", "Concrete", "500", "sqft", "$10,000"],
        ["Beam_B1", "Beam", "Steel", "120", "linear_ft", "$8,400"],
        ["HVAC_1", "HVAC", "Metal", "1", "unit", "$5,000"],
        ["Floor_C", "Floor", "Wood", "800", "sqft", "$16,000"]
    ]

    # Draw table grid
    # Vertical lines
    x_pos = table_x
    for width in col_widths:
        draw.line([(x_pos, table_y), (x_pos, table_y + row_height * (len(data_rows) + 1))],
                  fill='black', width=2)
        x_pos += width
    # Last vertical line
    draw.line([(x_pos, table_y), (x_pos, table_y + row_height * (len(data_rows) + 1))],
              fill='black', width=2)

    # Horizontal lines
    for i in range(len(data_rows) + 2):
        y_pos = table_y + i * row_height
        draw.line([(table_x, y_pos), (table_x + sum(col_widths), y_pos)],
                  fill='black', width=2)

    # Draw header text
    x_pos = table_x
    for i, header in enumerate(headers):
        draw.text((x_pos + 10, table_y + 15), header, fill='black', font=font_medium)
        x_pos += col_widths[i]

    # Draw data rows
    for row_idx, row_data in enumerate(data_rows):
        x_pos = table_x
        y_pos = table_y + (row_idx + 1) * row_height

        for col_idx, cell_text in enumerate(row_data):
            draw.text((x_pos + 10, y_pos + 15), cell_text, fill='black', font=font_small)
            x_pos += col_widths[col_idx]

    # Draw footer notes
    draw.text((50, table_y + row_height * (len(data_rows) + 1) + 30),
              "Notes: All materials must meet ASTM standards",
              fill='gray', font=font_small)

    # Save image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"✅ Test blueprint image created: {output_path}")
    print(f"   Size: {width}x{height}px")
    print(f"   Assets: {len(data_rows)}")


def create_low_quality_image(output_path: Path):
    """
    Create a low-quality image to test confidence gating.

    This image has poor clarity and should trigger low confidence scores.
    """
    # Create a smaller, blurrier image
    width, height = 600, 400
    img = Image.new('RGB', (width, height), color='lightgray')
    draw = ImageDraw.Draw(img)

    try:
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except:
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw degraded text
    draw.text((20, 20), "Asset Schedule (DEGRADED COPY)", fill='darkgray', font=font_medium)

    # Draw a simple table with poor contrast
    table_x = 40
    table_y = 80
    col_widths = [100, 80, 80, 60, 50]
    row_height = 35

    headers = ["Asset", "Type", "Mat.", "Qty", "Unit"]
    data_rows = [
        ["Wall_X", "Wall", "???", "200", "sqft"],
        ["Beam_Y", "Beam", "Steel", "50", "ft"],
    ]

    # Draw table with poor contrast (light gray on gray)
    x_pos = table_x
    for width in col_widths:
        draw.line([(x_pos, table_y), (x_pos, table_y + row_height * (len(data_rows) + 1))],
                  fill='darkgray', width=1)
        x_pos += width
    draw.line([(x_pos, table_y), (x_pos, table_y + row_height * (len(data_rows) + 1))],
              fill='darkgray', width=1)

    for i in range(len(data_rows) + 2):
        y_pos = table_y + i * row_height
        draw.line([(table_x, y_pos), (table_x + sum(col_widths), y_pos)],
                  fill='darkgray', width=1)

    # Draw text with poor contrast
    x_pos = table_x
    for i, header in enumerate(headers):
        draw.text((x_pos + 5, table_y + 10), header, fill='gray', font=font_small)
        x_pos += col_widths[i]

    for row_idx, row_data in enumerate(data_rows):
        x_pos = table_x
        y_pos = table_y + (row_idx + 1) * row_height

        for col_idx, cell_text in enumerate(row_data):
            draw.text((x_pos + 5, y_pos + 10), cell_text, fill='gray', font=font_small)
            x_pos += col_widths[col_idx]

    # Save image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"✅ Low-quality test image created: {output_path}")
    print(f"   Size: {width}x{height}px (degraded)")


if __name__ == "__main__":
    base_path = Path(__file__).parent.parent / 'data' / 'test_images'

    # Create high-quality test image
    create_test_blueprint_image(base_path / 'test_blueprint.png')

    # Create low-quality test image (for confidence gating test)
    create_low_quality_image(base_path / 'test_blueprint_low_quality.png')

    print("\n✅ All test images created successfully!")
    print(f"📁 Location: {base_path}")
