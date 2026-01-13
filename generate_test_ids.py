from PIL import Image, ImageDraw, ImageFont


def _font(size):
    try:
        return ImageFont.truetype("Arial.ttf", size)
    except:
        return ImageFont.load_default()


def make_aadhaar_like(path="fake_aadhaar_like.png"):
    img = Image.new("RGB", (900, 550), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 860, 510], outline="black", width=3)

    d.text((60, 60), "GOVERNMENT OF INDIA", fill="black", font=_font(34))
    d.text((60, 120), "Aadhaar (Sample)", fill="black", font=_font(26))
    d.text((60, 180), "Name: Rahul Sharma", fill="black", font=_font(24))
    d.text((60, 230), "DOB: 01/01/1998", fill="black", font=_font(24))
    d.text((60, 280), "Gender: M", fill="black", font=_font(24))
    d.text((60, 330), "Address: New Delhi, India", fill="black", font=_font(24))
    d.text((60, 390), "XXXX XXXX 1234", fill="black", font=_font(30))
    d.text((650, 390), "[QR]", fill="black", font=_font(28))

    img.save(path)
    print("Saved", path)


def make_pan_like(path="fake_pan_like.png"):
    img = Image.new("RGB", (900, 550), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 860, 510], outline="black", width=3)

    d.text((60, 60), "INCOME TAX DEPARTMENT", fill="black", font=_font(32))
    d.text((60, 120), "GOVT OF INDIA", fill="black", font=_font(28))
    d.text((60, 180), "Name: Rahul Sharma", fill="black", font=_font(24))
    d.text((60, 230), "Father's Name: Amit Sharma", fill="black", font=_font(24))
    d.text((60, 280), "DOB: 01/01/1998", fill="black", font=_font(24))
    d.text((60, 340), "PAN: ABCDE1234F", fill="black", font=_font(30))

    img.save(path)
    print("Saved", path)


if __name__ == "__main__":
    make_aadhaar_like()
    make_pan_like()
