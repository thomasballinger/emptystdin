

select returns stdin as ready to read even though it isn't.

The before-fix branch does this.

The master branch has this fixed by making the stdin read nonblocking.

