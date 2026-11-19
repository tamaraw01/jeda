import unittest
from calc import overdue
class Checks(unittest.TestCase):
 def test_boundary(self): self.assertFalse(overdue(45))
 def test_above(self): self.assertTrue(overdue(46))
 def test_below(self): self.assertFalse(overdue(44))
 def test_custom(self): self.assertFalse(overdue(30,30))
unittest.main()
