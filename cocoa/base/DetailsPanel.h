/* 
Copyright 2012 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#import <Cocoa/Cocoa.h>
#import <Python.h>
#import "PyDetailsPanel.h"

@interface DetailsPanel : NSWindowController
{
    IBOutlet NSTableView *detailsTable;
    
    PyDetailsPanel *model;
}
- (id)initWithPyRef:(PyObject *)aPyRef;
- (PyDetailsPanel *)model;

- (BOOL)isVisible;
- (void)toggleVisibility;

/* Python --> Cocoa */
- (void)refresh;
@end