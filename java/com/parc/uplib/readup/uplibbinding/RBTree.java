/*
  This file is part of the "UpLib 1.7.11" release.
  Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
  
  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/

package com.parc.uplib.readup.uplibbinding;

import java.util.*;

/**
 * A basic red-black tree from Cormon, Leiserson, and Rivest
 * @author Lance Good
 */
public class RBTree implements java.io.Serializable {
    public static int RED = 1;
    public static int BLACK = 2;

    public RBNode root;
    public RBNode nil;
    public Comparator comparator;

    protected Random random;

    public RBTree(Comparator comparator) {
        this.comparator = comparator;

        init();
    }

    protected void init() {
        // Create a random object for alternating between left and right
        // on equal keys
        random = new Random();

        // Create the nil node
        nil = createNil();
        nil.color = BLACK;
        nil.left = nil;
        nil.right = nil;

        // Set the root to nil of course
        root = nil;
    }

    /**
     * Factory method for nil node that subclasses can modify
     */
    protected RBNode createNil() {
        return new RBNode();
    }

    /**
     * TreeInsert from page 251 Cormon, Leiserson, and Rivest
     */
    protected void treeInsert(RBNode z) {
        RBNode y = nil;
        RBNode x = root;

        while (x != nil) {
            y = x;

            // Randomly choose between left and right if keys equal
            if (comparator.compare(z.key, x.key) == 0) {
                if (random.nextBoolean()) {
                    x = x.left;
                }
                else {
                    x = x.right;
                }
            }
            else if (comparator.compare(z.key, x.key) < 0) {
                x = x.left;
            }
            else {
                x = x.right;
            }
        }

        z.parent = y;

        if (y == nil) {
            root = z;
        }
        else {
            // Randomly choose between left and right if keys equal
            if (comparator.compare(z.key, y.key) == 0) {
                if (y.left == nil && y.right == nil) {
                    if (random.nextBoolean()) {
                        y.left = z;
                    }
                    else {
                        y.right = z;
                    }
                }
                else if (y.left == nil) {
                    y.left = z;
                }
                else if (y.right == nil) {
                    y.right = z;
                }
                else {
                    System.err.println("Error in treeInsert!");
                }
            }
            else if (comparator.compare(z.key, y.key) < 0) {
                y.left = z;
            }
            else {
                y.right = z;
            }
        }

        z.left = nil;
        z.right = nil;
    }

    /**
     * Left rotate from page 266 Cormon, Leiserson, and Rivest
     */
    protected void leftRotate(RBNode x) {
        RBNode y = x.right;
        x.right = y.left;

        if (y.left != nil) {
            y.left.parent = x;
        }

        y.parent = x.parent;

        if (x.parent == nil) {
            root = y;
        }
        else {
            if (x == x.parent.left) {
                x.parent.left = y;
            }
            else {
                x.parent.right = y;
            }
        }
        y.left = x;
        x.parent = y;
    }

    /**
     * Left rotate inverted from page 266 Cormon, Leiserson, and Rivest
     */
    protected void rightRotate(RBNode x) {
        RBNode y = x.left;
        x.left = y.right;

        if (y.right != nil) {
            y.right.parent = x;
        }

        y.parent = x.parent;

        if (x.parent == nil) {
            root = y;
        }
        else {
            if (x == x.parent.right) {
                x.parent.right = y;
            }
            else {
                x.parent.left = y;
            }
        }
        y.right = x;
        x.parent = y;
    }

    /**
     * RB-Insert from page 268 of Cormon, Lieserson, and Rivest
     */
    public void rbInsert(RBNode x) {
        RBNode y = nil;

        treeInsert(x);
        x.color = RED;
        while (x != root && x.parent.color == RED) {

            if (x.parent == x.parent.parent.left) {
                y = x.parent.parent.right;
                if (y.color == RED) {
                    x.parent.color = BLACK;
                    y.color = BLACK;
                    x.parent.parent.color = RED;
                    x = x.parent.parent;
                }
                else {
                    if (x == x.parent.right) {
                        x = x.parent;
                        leftRotate(x);
                    }
                    x.parent.color = BLACK;
                    x.parent.parent.color = RED;
                    rightRotate(x.parent.parent);
                }
            }
            else {
                y = x.parent.parent.left;
                if (y.color == RED) {
                    x.parent.color = BLACK;
                    y.color = BLACK;
                    x.parent.parent.color = RED;
                    x = x.parent.parent;
                }
                else {
                    if (x == x.parent.left) {
                        x = x.parent;
                        rightRotate(x);
                    }
                    x.parent.color = BLACK;
                    x.parent.parent.color = RED;
                    leftRotate(x.parent.parent);
                }
            }
        }
        root.color = BLACK;
    }

    /**
     * Tree Minimum from page 248 Cormon, Leiserson, and Rivest
     */
    protected RBNode treeMinimum(RBNode x) {
        while (x.left != nil) {
            x = x.left;
        }
        return x;
    }

    /**
     * TreeSuccessor from page 249 Cormon, Leiserson, and Rivest
     */
    protected RBNode treeSuccessor(RBNode x) {
        if (x.right != nil) {
            return treeMinimum(x.right);
        }

        RBNode y = x.parent;
        while (y != nil && x == y.right) {
            x = y;
            y = y.parent;
        }
        return y;
    }

    /**
     * RB-Delete-Fixup from page 274 Cormon, Leiserson, and Rivest
     */
    protected void rbDeleteFixup(RBNode x) {
        RBNode w = nil;

        while (x != root && x.color == BLACK) {
            if (x == x.parent.left) {
                w = x.parent.right;
                if (w.color == RED) {
                    w.color = BLACK;
                    x.parent.color = RED;
                    leftRotate(x.parent);
                    w = x.parent.right;
                }
                if (w.left.color == BLACK && w.right.color == BLACK) {
                    w.color = RED;
                    x = x.parent;
                }
                else {
                    if (w.right.color == BLACK) {
                        w.left.color = BLACK;
                        w.color = RED;
                        rightRotate(w);
                        w = x.parent.right;
                    }
                    w.color = x.parent.color;
                    x.parent.color = BLACK;
                    w.right.color = BLACK;
                    leftRotate(x.parent);
                    x = root;
                }
            }
            else {
                w = x.parent.left;
                if (w.color == RED) {
                    w.color = BLACK;
                    x.parent.color = RED;
                    rightRotate(x.parent);
                    w = x.parent.left;
                }
                if (w.right.color == BLACK && w.left.color == BLACK) {
                    w.color = RED;
                    x = x.parent;
                }
                else {
                    if (w.left.color == BLACK) {
                        w.right.color = BLACK;
                        w.color = RED;
                        leftRotate(w);
                        w = x.parent.left;
                    }
                    w.color = x.parent.color;
                    x.parent.color = BLACK;
                    w.left.color = BLACK;
                    rightRotate(x.parent);
                    x = root;
                }
            }
        }
        x.color = BLACK;
    }

    /**
     * RB-Delete from page 273 Cormon, Leiserson, and Rivest
     */
    protected RBNode rbDelete(RBNode z) {
        RBNode y = nil;
        RBNode x = nil;

        if (z.left == nil || z.right == nil) {
            y = z;
        }
        else {
            y = treeSuccessor(z);
        }

        if (y.left != nil) {
            x = y.left;
        }
        else {
            x = y.right;
        }

        x.parent = y.parent;

        if (y.parent == nil) {
            root = x;
        }
        else {
            if (y == y.parent.left) {
                y.parent.left = x;
            }
            else {
                y.parent.right = x;
            }
        }

        if (y != z) {
            z.key = y.key;
        }

        if (y.color == BLACK) {
            rbDeleteFixup(x);
        }

        return y;
    }

    /**
     * Iterative tree search from page 248 Cormon, Leiserson, and Rivest
     */
    protected RBNode iterativeTreeSearch(RBNode x, Object key) {
        while (x != nil && comparator.compare(key, x.key) != 0) {
            if (comparator.compare(key, x.key) < 0) {
                x = x.left;
            }
            else {
                x = x.right;
            }
        }

        return x;
    }

    /**
     * Inserts the value into the tree
     */
    public void insert(Object key) {
        RBNode node = new RBNode();
        node.key = key;
        rbInsert(node);
    }

    /**
     * Delete the value from the tree
     */
    public void delete(Object key) {
        RBNode node = iterativeTreeSearch(root, key);
        if (node != nil) {
            rbDelete(node);
        }
    }

    /**
     * Does the tree contain the specified object
     */
    public boolean contains(Object key) {
        RBNode node = iterativeTreeSearch(root, key);
        if (node != nil) {
            return true;
        }
        else {
            return false;
        }
    }
	
    protected class RBNode implements java.io.Serializable {
        public RBNode parent;
        public RBNode right;
        public RBNode left;
        public int color;
        public Object key;
    }
}
