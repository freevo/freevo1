#include <stdio.h>
#include "freevo_text.h"
#include "freevo_icon.h"

// A gimp image 128 x 128 saved as "c source code header"
// The name of the files and the static variables are changed
// the colours are converted to 16 level of grey
int convert2goom(const char *image_name, char *image_data, int width, int height)
{
    char *data = image_data;
    unsigned char pixel[3];
    int x, y, i, average, value;
    printf("static Motif %s = {\n    ", image_name);
    for (y = 0; y < height; y++) {
        i = 0;
        for (x = 0; x < width; x++) {
            HEADER_PIXEL(data, pixel);
            average = (pixel[0]+1 + pixel[1]+1 + pixel[2]+1) / 3 - 1;
            value = average / 16;
            printf("%d,", value);
            i++;
            if (i % 16 == 0) {
                printf("\n    ");
            }
        }
    }
    printf("};\n");

    return 0;
}

int main(int argc, char *argv[])
{
    convert2goom("CONV_MOTIF1", freevo_text, freevo_text_width, freevo_text_height);
    convert2goom("CONV_MOTIF2", freevo_icon, freevo_icon_width, freevo_icon_height);

    return 0;
}
