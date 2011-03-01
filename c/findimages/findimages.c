/*
 * This file is part of the "UpLib 1.7.11" release.
 * Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */
/*
 * This code is based on the example program "prog/pagesegtest2.c", from
 * the leptonica library from http://leptonica.org/, most of which is
 * written by Dan Bloomberg.  The original Leptonica copyright on the
 * original code is reproduced below.
 */

/*====================================================================*
 -  Copyright (C) 2001 Leptonica.  All rights reserved.
 -  This software is distributed in the hope that it will be
 -  useful, but with NO WARRANTY OF ANY KIND.
 -  No author or distributor accepts responsibility to anyone for the
 -  consequences of using this software, or for whether it serves any
 -  particular purpose or works at all, unless he or she says so in
 -  writing.  Everyone is granted permission to copy, modify and
 -  redistribute this source code, for commercial or non-commercial
 -  purposes, with the following restrictions: (1) the origin of this
 -  source code must not be misrepresented; (2) modified versions must
 -  be plainly marked as such; and (3) this notice may not be removed
 -  or altered from any source or modified source distribution.
 *====================================================================*/

#include <stdio.h>
#include <stdlib.h>
#include "allheaders.h"

#ifdef LIBLEPT_GT_1_50
#define HISTOGRAM_FUNCTION(p)  (pixGetGrayHistogram((p),1))
#else
#define HISTOGRAM_FUNCTION(p)  (pixGetHistogram(p))
#endif


main(int    argc,  char **argv)
{
    int debug = 0;
    l_int32      index, zero;
    char        *filein, *fileout, *wordboxes_file;
    BOXA        *boxatm, *boxahm, *boxnth, *wboxes, *boxccl;
    NUMA        *hist;
    PIX         *pixo;          /* input image, say, at 300 ppi */
    PIX         *pixg;   /* input image, say, at 300 ppi, grayscale */
    PIX         *pixs;      /* input image, say, at 300 ppi, binary */
    PIX         *pixr;          /* image reduced to 150 ppi */
    PIX         *pixhs;         /* image of halftone seed, 150 ppi */
    PIX         *pixm;      /* image of mask of components, 150 ppi */
    PIX         *pixhm1;        /* image of halftone mask, 150 ppi */
    PIX         *pixhm2;        /* image of halftone mask, 300 ppi */
    PIX         *pixhm3;        /* image of halftone mask, clipped to original dimensions */
    PIX         *pixht;    /* image of halftone components, 150 ppi */
    PIX         *pixnht; /* image without halftone components, 150 ppi */
    PIX         *pixi;          /* inverted image, 150 ppi */
    PIX         *pixvws;   /* image of vertical whitespace, 150 ppi */
    PIX         *pixtm1;      /* image of closed textlines, 150 ppi */
    PIX         *pixtm2; /* image of refined text line mask, 150 ppi */
    PIX         *pixtm3; /* image of refined text line mask, 300 ppi */
    PIX         *pixtb1;       /* image of text block mask, 150 ppi */
    PIX         *pixtb2;       /* image of text block mask, 300 ppi */
    PIX         *pixnon;  /* image of non-text or halftone, 150 ppi */
    PIX         *pixseed4;
    PIX         *pixmask4;     
    PIX         *pixsf4;     
    PIX         *pixd4;     
    PIX         *pixhm4;     
    PIX         *pixcci;
    PIX         *pixt1, *pixt2, *pixt3, *pixt4, *pixt5;
    PIXCMAP     *cmap;
    PTAA        *ptaa;
    static char  mainName[] = "findimages";
    l_int32      maxGrayVal;
    l_float32    maxCount, dpi, minsize;

    if ((argc < 4) || (argc > 6))
      exit(ERROR_INT(" Syntax:  findimages [--debug] DPI PAGEIMAGE WORDBOXES [OUTFILE]", mainName, 1));

    int argp = 1;
    if (strcmp(argv[argp], "--debug") == 0) {
      debug = 1;
      argp += 1;
    }
    dpi = atof(argv[argp]);
    minsize = (72/dpi) * (72/dpi);
    filein = argv[argp+1];
    wordboxes_file = argv[argp+2];
    fileout = (argc > (argp+3)) ? argv[argp+3] : "-";

    if ((pixo = pixRead(filein)) == NULL)
      exit(ERROR_INT("pixs not made", mainName, 1));

    /* Get a 1 bpp version of the page */

    if (pixGetDepth(pixo) > 1) {
        cmap = pixGetColormap(pixo);
        if (pixGetDepth(pixo) == 32)
          pixg = pixConvertRGBToGray(pixo, 0.3, 0.59, 0.11);
        else if (cmap != 0) {
            pixg = pixRemoveColormap(pixo, REMOVE_CMAP_BASED_ON_SRC);
            if (pixGetDepth(pixg) == 32)
              pixg = pixConvertRGBToGray(pixg, 0.3, 0.59, 0.11);
        }

        /* pixg is now grayscale */
        if (pixGetDepth(pixg) > 1) {

            /* Figure out the threshold value */
            hist = HISTOGRAM_FUNCTION(pixg);

#if 0
            {
                int i, j, count, red, green, blue;
                l_float32 luminance;
                count = numaGetCount(hist);
                for (i = 0;  i < count;  i++) {
                    numaGetIValue(hist, i, &j);
                    if (j > 0) 
                      fprintf(stderr, "  %5d:%10.1f (%d,%d,%d):%d\n", i, (float) i, i, i, i, j);
                }
                pixGetAverageMasked(pixg, NULL, 0, 0, 1, &luminance);
                fprintf(stderr, "average pixel is %f\n", luminance);
            }
#endif

            {
                l_int32 least, most, i, j, count;
                count = numaGetCount(hist);
                for (i = 0, least=0;  i < count;  least = i, i++) {
                    if (numaGetIValue(hist, i, &j), j > 0) {
                        /* fprintf(stderr, "least %d: %d\n", i, j); */
                        break;
                    }
                }
                for (i = count-1, most=i;  i >= 0;  i--, most--) {
                    if (numaGetIValue(hist, i, &j), j > 0) {
                        /* fprintf(stderr, "most %d: %d\n", i, j); */
                        break;
                    }
                }
                if ((least > 0) || (most < (1 << pixGetDepth(pixg))-1)) {
                    /* rescale colors to maximize contrast */
                    /* pixDisplayWithTitle(pixg, 0, 0, "foo1"); */
                    pixg = pixGammaTRC(pixg, pixg, 1.0, least, most);
                    hist = HISTOGRAM_FUNCTION(pixg);
#if 0
                    {
                        int i, j, count, red, green, blue;
                        count = numaGetCount(hist);
                        for (i = 0;  i < count;  i++) {
                            numaGetIValue(hist, i, &j);
                            if (j > 0) 
                              fprintf(stderr, "  %5d:%10.1f (%d,%d,%d):%d\n", i, (float) i, i, i, i, j);
                        }
                    }
#endif
                    if (debug)
                      pixDisplayWithTitle(pixg, 0, 0, "maximized contrast", 1);
                }
            }

            pixGetAverageMasked(pixg, NULL, 0, 0, 1, L_MEAN_ABSVAL, &maxCount);
            maxGrayVal = abs((int) (maxCount + 0.5));

            /* fprintf(stderr, "average %d\n", maxGrayVal); */
            if (maxGrayVal < 128) {
                /* invert the image */
                pixg = pixInvert(pixg, pixg);
                maxGrayVal = 255 - maxGrayVal;
            }

#if 0
            /* now quantize, hoping the background winds up all one color... */
            pixg = pixThresholdTo4bpp(pixg, 16, 0);
            hist = HISTOGRAM_FUNCTION(pixg);
            numaGetMax(hist, &maxCount, &maxGrayVal);
            fprintf(stderr, "max %d (%f)\n", maxGrayVal, maxCount);
            /* ...and threshold to that color */
            pixg = pixGammaTRC(pixg, pixg, 1.0, 0, maxGrayVal);
#endif
            pixs = pixThresholdToBinary(pixg, maxGrayVal);
            if (debug)
              pixDisplayWithTitle(pixs, 0, 0, "thresholded", 1);
        } else {
            pixs = pixClone(pixg);
        }
    } else {
        pixs = pixClone(pixo);
    }

    if (debug)
      pixDisplayWithTitle(pixs, 0, 0, "original monochrome", 1);

    /* if sizes not divisible by 16, pad at left and right edges */
    {
        int w = pixGetWidth(pixs);
        int h = pixGetHeight(pixs);
        if ((w % 64) != 0)
          w = 64 - (w % 64);
        else
          w = 0;
        if ((h % 64) != 0)
          h = 64 - (h % 64);
        else
          h = 0;
        if ((w != 0) || (h != 0))
          pixs = pixAddBorderGeneral(pixs, 0, w, 0, h, 0);
    }

    if (strcmp(wordboxes_file, "-") != 0) {
        /* Read the wordboxes file */
        wboxes = boxaRead(wordboxes_file);

        /* mask out the wordboxes */
        {
            int i, count;
            BOX *b;
            count = boxaGetCount(wboxes);
            for (i = 0;  i < count;  i++) {
                b = boxaGetBox(wboxes, i, L_CLONE);
                pixRasterop(pixs, b->x, b->y, b->w, b->h, PIX_CLR, NULL, 0, 0);
            }
        }
    }

    if (debug)
      pixDisplayWithTitle(pixs, 0, 0, "wordboxes removed", 1);

    {
        /* remove single black pixels surrounded by white */
        pixInvert(pixs, pixs);
        pixs = pixCloseBrick(pixs, pixs, 3, 3);
        pixInvert(pixs, pixs);
        pixCloseBrick(pixs, pixs, 3, 3);
    }

    if (debug)
      pixDisplayWithTitle(pixs, 0, 0, "pepper removed", 1);

    pixcci = pixCreate(pixGetWidth(pixo), pixGetHeight(pixo), 1);
    boxccl = pixConnCompBB(pixs, 4);
/*
    boxccl = boxaRemoveSmallComponents(boxccl, 150, 150, L_REMOVE_IF_BOTH, NULL);
*/
    /* Reduce to 150 ppi */
    pixt1 = pixScaleToGray2(pixs);

    if (debug)
      pixDisplayWithTitle(pixt1, 0, 0, "scaled to 150 dpi", 1);

    {
        int i, count;
        BOX *b;
        count = boxaGetCount(boxccl);
        for (i = 0;  i < count;  i++) {
            b = boxaGetBox(boxccl, i, L_CLONE);
            if (((b->w/dpi) > 0.5) || ((b->h/dpi) > 0.5))
              pixRasterop(pixcci, b->x, b->y, b->w, b->h, PIX_SET, NULL, 0, 0);
            /* fprintf(stderr, "cc %d %d %d %d\n", b->x, b->y, b->w, b->h); */
        }
    }

    pixr = pixReduceRankBinaryCascade(pixs, 2, 0, 0, 0);

    /* Get seed for halftone parts */

    /* this code doesn't pick up illustrations with lots of open space
       containing vertical lines -- pictures of text, in other words.
       Probably have to fiddle with the parameters a bit.
       */
    pixt1 = pixReduceRankBinaryCascade(pixr, 4, 4, 3, 0);
    pixt2 = pixOpenBrick(NULL, pixt1, 5, 5);
    pixhs = pixExpandBinaryPower2(pixt2, 8);
    pixDestroy(&pixt1);
    pixDestroy(&pixt2);

    if (debug)
      pixDisplayWithTitle(pixhs, 80, 60, "halftone seed", 1);

    /* Get mask for connected regions */
    pixt1 = pixReduceRankBinaryCascade(pixs, 1, 0, 0, 0);
    pixm = pixCloseBrick(NULL, pixt1, 4, 4);
    pixDestroy(&pixt1);

    if (debug)
      pixDisplayWithTitle(pixm, 120, 90, "halftone seed mask", 1);

    /* Fill seed into mask to get halftone mask */
    pixhm1 = pixSeedfillBinary(NULL, pixhs, pixm, 4);

    if (debug)
      pixDisplayWithTitle(pixhm1, 160, 120, "halftone mask", 1);
    
    /* Now do the halftone mask a la pagesegtest3, to get those
       areas which look a lot like text. */

    /* Make seed and mask, and fill seed into mask */
    pixseed4 = pixMorphSequence(pixs, "r1143 + o5.5+ x4", 0);
    pixmask4 = pixMorphSequence(pixs, "r11", 0);
    pixsf4 = pixSeedfillBinary(NULL, pixseed4, pixmask4, 8);
    pixd4 = pixMorphSequence(pixsf4, "d3.3", 0);

    /* Mask at half resolution */
    pixhm4 = pixExpandBinaryPower2(pixd4, 2);
    
    /* Add two halftone masks */
    pixhm1 = pixOr(pixhm1, pixhm1, pixhm4);

    /* Extract halftone stuff */
    pixht = pixAnd(NULL, pixhm1, pixr);

    if (debug)
      pixDisplayWithTitle(pixht, 200, 150, "halftone stuff", 1);

    /* Extract non-halftone stuff */
    pixnht = pixXor(NULL, pixht, pixr);

    pixnht = pixSelectBySize(pixnht, 8, 8, 4, L_SELECT_IF_EITHER,
                             L_SELECT_IF_GTE, NULL);

    if (debug)
      pixDisplayWithTitle(pixnht, 240, 180, "line art", 1);

    pixnht = pixCloseBrick(NULL, pixnht, (int)(dpi/72), (int)(dpi/72));

    if (debug)
      pixDisplayWithTitle(pixnht, 240, 180, "line art after dilation", 1);

    pixnht = pixExpandBinaryPower2(pixnht, 2);

#if 0

    /* Get bit-inverted image */
    pixi = pixInvert(NULL, pixnht);
    /*
      pixWrite("junk_invert.150.png", pixi, IFF_PNG);
      pixDisplayWithTitle(pixi, 280, 210, "inverted non-halftone", 1);
      */
    /* Identify vertical whitespace by opening inverted image */
    pixt1 = pixOpenBrick(NULL, pixi, 5, 1); /* removes thin vertical lines */
    pixvws = pixOpenBrick(NULL, pixt1, 1, 200); /* gets long vertical lines */
    pixDestroy(&pixt1);
    pixDisplayWithTitle(pixvws, 320, 240, "whitespace mask");
    /*
      pixWrite("junk_vertws.150.png", pixvws, IFF_PNG);
      */
    /* Get proto (early processed) text line mask */
    /* first close the characters and words in the textlines */
    pixtm1 = pixCloseBrick(NULL, pixnht, 30, 1);
    /*
      pixWrite("junk_textmask1.150.png", pixtm1, IFF_PNG);
      pixDisplayWithTitle(pixtm1, 360, 270, "textline mask 1");
      */
    /* Next open back up the vertical whitespace corridors */
    pixtm2 = pixSubtract(NULL, pixtm1, pixvws);
    /*
      pixWrite("junk_textmask2.150.png", pixtm2, IFF_PNG);
      pixDisplayWithTitle(pixtm2, 400, 300, "textline mask 2");
      */
    /* Do a small opening to remove noise */
    pixOpenBrick(pixtm2, pixtm2, 3, 3);
    /*
      pixWrite("junk_textmask3.150.png", pixtm2, IFF_PNG);
      pixDisplayWithTitle(pixtm2, 400, 300, "textline mask 3");
      */
    /* Join pixels vertically to make text block mask */
    pixtb1 = pixCloseBrick(NULL, pixtm2, 1, 10);
    /*
      pixWrite("junk_textblock1.150.png", pixtb1, IFF_PNG);
      pixDisplayWithTitle(pixtb1, 440, 330, "textblock mask");
      */

    pixZero (pixtb1, &zero);
    if (!zero) {
        /* Solidify the textblock mask and remove noise:
         *  (1) Close the blocks and dilate slightly to form a solid mask.
         *  (2) Open the result to form a seed.
         *  (3) Fill from seed into mask, to remove the noise.
         *  (4) Expand the result to full res.  */
        pixt1 = pixMorphSequenceByComponent(pixtb1, "c30.30 + d3.3", 8, 0, 0, NULL);
        pixt2 = pixMorphSequenceByComponent(pixt1, "o20.20", 8, 0, 0, NULL);
        pixt3 = pixSeedfillBinary(NULL, pixt1, pixt2, 8);
        pixtb2 = pixExpandBinary(pixt3, 2);
        pixDestroy(&pixt1);
        pixDestroy(&pixt2);
        pixDestroy(&pixt3);
        /*
          pixWrite("junk_textblock2.300.png", pixtb2, IFF_PNG);
          pixDisplayWithTitle(pixtb2, 480, 360, "textblock mask");
          */

        /* Expand line masks to full resolution, and fill into the original */
        pixtm3 = pixExpandBinary(pixtm2, 2);
        pixt1 = pixSeedfillBinary(NULL, pixtm3, pixs, 8);
        pixOr(pixtm3, pixtm3, pixt1);
        pixDestroy(&pixt1);
        /*
          pixWrite("junk_textmask.300.png", pixtm3, IFF_PNG);
          pixDisplayWithTitle(pixtm3, 480, 360, "textline mask 4");
          */
    }

#endif

    pixhm2 = pixExpandBinaryPower2(pixhm1, 2);
    pixt1 = pixSeedfillBinary(NULL, pixhm2, pixs, 8);
    if (!zero) {
        pixOr(pixhm2, pixhm2, pixt1);
        pixDestroy(&pixt1);
    }
    /*
      pixWrite("junk_htmask.300.png", pixhm2, IFF_PNG);
      pixDisplayWithTitle(pixhm2, 520, 390, "halftonemask 2");
      */

#if 0
    /* Find objects that are neither text nor halftones */
    if (!zero)
      pixt1 = pixSubtract(NULL, pixs, pixtm3); /* remove text pixels */
    else
      pixt1 = pixClone(pixs);
    pixnon = pixSubtract(NULL, pixt1, pixhm2); /* remove halftone pixels */
    pixDisplayWithTitle(pixnon, 540, 420, "other stuff (neither text nor halftone)", 1);
#endif
    /*
      pixWrite("junk_other.300.png", pixnon, IFF_PNG);
      */
    pixDestroy(&pixt1);
/*
    pixWrite("junk_pixhm2.300.png", pixhm2, IFF_PNG);
*/
    /* clip to original size */
    pixhm3 = pixCreate(pixGetWidth(pixo), pixGetHeight(pixo), 1);
    pixRasterop(pixhm3, 0, 0, pixGetWidth(pixo), pixGetHeight(pixo), PIX_SRC, pixhm2, 0, 0);
    pixhm3 = pixOr(pixhm3, pixhm3, pixcci);
    pixhm3 = pixOr(pixhm3, pixhm3, pixnht);

    if (debug)
      pixDisplayWithTitle(pixhm3, 500, 500, "final image", 1);
/*
    pixWrite("junk_pixhm3.300.png", pixhm3, IFF_PNG);
*/
/*
    pixDisplayWithTitle(pixhm2, 520, 390, "halftonemask 2");
*/
    /* Write out b.b. for text line mask and halftone mask components */
    boxahm = pixConnComp(pixhm3, NULL, 8);
    /*
      boxnth = pixConnComp(pixnon, NULL, 8);
      */
    /*
      boxaWrite("junk_textmask.boxa", boxatm);
      */

    FILE *outputstream = (strcmp(fileout, "-") == 0) ? stdout : fopen(fileout, "w");
    int i, j;
    l_int32 result;
    int count = boxaGetCount(boxahm);
    BOX *b, *b2;
    /* check for subboxes */
    boxahm = boxaSort(boxahm, L_SORT_BY_AREA, L_SORT_DECREASING, NULL);
    char *flags = malloc(count * sizeof(char));
    for (i = 0;  i < count;  i++)
      flags[i] = 0;
    for (i = 0;  i < count;  i++) {
        if (flags[i] == 0) {
            b = boxaGetBox(boxahm, i, L_CLONE);
            if ((b->w * b->h) > minsize)
              fprintf(outputstream, "halftone %d %d %d %d\n", b->x, b->y, b->w, b->h);
            flags[i] = 1;
            /* now find boxes inside this one */
            for (j = i+1;  j < count;  j++) {
                b2 = boxaGetBox(boxahm, j, L_CLONE);
                if (boxContains(b, b2, &result), result == 1) {
                    flags[j] = 1;
                }
            }
        }
    }
#if 0
    count = boxaGetCount(boxnth);
    for (i = 0;  i < count;  i++) {
        b = boxaGetBox(boxnth, i, L_CLONE);
        if ((b->w > 8) && (b->h > 8))
          fprintf(outputstream, "misc %d %d %d %d\n", b->x, b->y, b->w, b->h);
    }
#endif
    /*
      pixWrite(fileout, pixtm3, IFF_PNG);
      */

#if 0
    /* clean up to test with valgrind */
    pixDestroy(&pixs);
    pixDestroy(&pixr);
    pixDestroy(&pixhs);
    pixDestroy(&pixm);
    pixDestroy(&pixhm1);
    pixDestroy(&pixhm2);
    pixDestroy(&pixht);
    pixDestroy(&pixnht);
    pixDestroy(&pixi);
    pixDestroy(&pixvws);
    pixDestroy(&pixtm1);
    pixDestroy(&pixtm2);
    pixDestroy(&pixtm3);
    pixDestroy(&pixtb1);
    pixDestroy(&pixtb2);
    pixDestroy(&pixnon);
    boxaDestroy(&boxatm);
    boxaDestroy(&boxahm);
#endif
    exit(0);
}

