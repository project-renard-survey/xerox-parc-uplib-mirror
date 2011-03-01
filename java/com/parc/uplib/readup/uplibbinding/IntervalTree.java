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
 * A basic interval tree from Cormon, Leiserson, and Rivest
 * @author Lance Good
 */
public class IntervalTree extends RBTree implements java.io.Serializable {

    /**
     * Constructor to create an interval comparator
     */
    public IntervalTree() {
        super(new IntervalComparator());
    }

    /**
     * Constructor to create an interval comparator
     */
    public IntervalTree(Comparator c) {
        super(c);
    }

    /**
     * Create a nil node
     */
    protected RBNode createNil() {
        return new IntervalNode();
    }

    /**
     * Updates the max value of a node by checking itself vs. its children
     */
    protected void updateMax(IntervalNode x) {
        if (x.left != nil && x.right != nil) {
            x.max = Math.max(((Interval) x.key).high, Math.max(((IntervalNode) x.left).max, ((IntervalNode) x.right).max));
        }
        else if (x.left != nil) {
            x.max = Math.max(((Interval) x.key).high, ((IntervalNode) x.left).max);
        }
        else if (x.right != nil) {
            x.max = Math.max(((Interval) x.key).high, ((IntervalNode) x.right).max);
        }
        else {
            x.max = ((Interval) x.key).high;
        }
    }

    /**
     * Updates the max value of a node by checking itself vs. its children
     */
    protected void updateMin(IntervalNode x) {
        if (x.left != nil && x.right != nil) {
            x.min = Math.min(((Interval) x.key).low, Math.min(((IntervalNode) x.left).min, ((IntervalNode) x.right).min));
        }
        else if (x.left != nil) {
            x.min = Math.min(((Interval) x.key).low, ((IntervalNode) x.left).min);
        }
        else if (x.right != nil) {
            x.min = Math.min(((Interval) x.key).low, ((IntervalNode) x.right).min);
        }
        else {
            x.min = ((Interval) x.key).low;
        }		
    }

    /**
     * Overridden left rotate to update the max and min values
     */
    protected void leftRotate(RBNode x) {
        super.leftRotate(x);

        // Update the max values of x and its parent
        updateMax((IntervalNode) x);
        updateMax((IntervalNode) x.parent);
        updateMin((IntervalNode) x);
        updateMin((IntervalNode) x.parent);
    }

    /**
     * Overridden right rotate to update the max and min values
     */
    protected void rightRotate(RBNode x) {
        super.rightRotate(x);

        // Update the max values of x and its parent
        updateMax((IntervalNode) x);
        updateMax((IntervalNode) x.parent);
        updateMin((IntervalNode) x);
        updateMin((IntervalNode) x.parent);
    }

    /**
     * Updates the max at the specified node by comparing only against the
     * new value
     */
    protected void updateMax(IntervalNode x, Interval y) {
        x.max = Math.max(x.max, y.high);
    }

    /**
     * Updates the min at the specified node by comparing only against the
     * new value
     */
    protected void updateMin(IntervalNode x, Interval y) {
        x.min = Math.min(x.min, y.low);
    }

    /**
     * Modified TreeInsert from page 251 Cormon, Leiserson, and Rivest
     */
    protected void treeInsert(RBNode z) {
        RBNode y = nil;
        RBNode x = root;

        while (x != nil) {
            y = x;

            // Update y's max value
            updateMax((IntervalNode) y, (Interval) z.key);
            updateMin((IntervalNode) y, (Interval) z.key);

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
            // If left and right are both null then randomly
            // choose between left and right if keys equal
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
                    System.err.println("Error in TreeInsert!");
                }
            }
            else if (comparator.compare(z.key, y.key) < 0) {
                y.left = z;
            }
            else {
                y.right = z;
            }
        }

        ((IntervalNode) z).max = ((Interval) z.key).high;
        z.left = nil;
        z.right = nil;
    }

    /**
     * Updates max values for the entire tree
     */
    protected void updateTreeMax(RBNode x) {
        if (x.left != nil) {
            updateTreeMax(x.left);
        }
        if (x.right != nil) {
            updateTreeMax(x.right);
        }
        if (x != nil) {
            updateMax((IntervalNode) x);
        }
    }

    /**
     * Updates min values for the entire tree 
     */
    protected void updateTreeMin(RBNode x) {
        if (x.left != nil) {
            updateTreeMin(x.left);
        }
        if (x.right != nil) {
            updateTreeMin(x.right);
        }
        if (x != nil) {
            updateMin((IntervalNode) x);
        }		
    }

    /**
     * Modified RB-Delete from page 273 Cormon, Leiserson, and Rivest
     */
    protected RBNode rbDelete(RBNode z) {
        RBNode node = super.rbDelete(z);

        updateTreeMax(root);
        updateTreeMin(root);

        return node;
    }

    /**
     * Determine whether these two intervals overlap - overlapping end points aren't considered to be overlapping
     */
    protected boolean overlaps(Interval i1, Interval i2) {
        if ((i1.low >= i2.low && i1.low < i2.high) || (i1.high > i2.low && i1.high <= i2.high) || (i1.low <= i2.low && i1.high >= i2.high)) {
            return true;
        }
        else {
            return false;
        }
    }

    public void intervalSearch(Interval i, ArrayList allObjs) {
        intervalSearch(i,allObjs,root);
    }

    protected void intervalSearch(Interval i, ArrayList allObjs, RBNode node) {
        if (node.left != nil && ((IntervalNode)node.left).max > i.low) {
            intervalSearch(i,allObjs,node.left);	 
        }
		
        if (node != nil && overlaps((Interval)node.key,i)) {
            allObjs.add(node.key);
        }
				
        if (node.right != nil && ((IntervalNode)node.right).min < i.high) {
            intervalSearch(i,allObjs,node.right);				
        }		
    }

    /**
     * Determine whether the given interval overlaps some interval in the tree
     */
    public Object intervalSearch(Interval i) {
        RBNode x = root;

        while (x != nil && !overlaps(i, (Interval) x.key)) {
            if (x.left != nil && ((IntervalNode) x.left).max >= i.low) {
                x = x.left;
            }
            else {
                x = x.right;
            }
        }

        if (x == nil) {
            return null;
        }
        else {
            return x.key;
        }
    }

    /**
     * Inserts the value into the tree
     */
    public void insert(Object key) {
        IntervalNode node = new IntervalNode();
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

    /**
     * A simple interval with high and low values and a user object.
     */
    public static class Interval implements java.io.Serializable {
        public double low;
        public double high;
        public Object userObj;

        public String toString() {
            return "[" + low + "-" + high + "]";
        }
    }

    /**
     * Comparator for intervals
     */
    public static class IntervalComparator implements Comparator, java.io.Serializable {
        /**
         * Compares two interval objects
         */
        public int compare(Object o1, Object o2) {
            if (((Interval) o1).low < ((Interval) o2).low) {
                return -1;
            }
            else if (((Interval) o1).low == ((Interval) o2).low) {
                return 0;
            }
            else {
                return 1;
            }
        }
    }
	
    public static void printDepthFirst(RBTree tree, RBNode node) {
        if (node.left != tree.nil) {
            printDepthFirst(tree,(IntervalNode)node.left);
        }
        System.out.println(node.key.toString());
        if (node.right != tree.nil) {
            printDepthFirst(tree,(IntervalNode)node.right);
        }
    }
	
    protected class IntervalNode extends RBNode {
        public double max;
        public double min;
    }	
}
