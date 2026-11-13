# Image chooser regression — extension 1.3.20

The 1.3.19 ownership filter required the media node's closest post container to equal the outer selected post. That was too strict: Facebook can use nested article semantics around the selected post's own photo/video. This could silently send an image post into caption-only preview.

1.3.20 allows structural photo/video wrappers within the selected post. It excludes explicitly identified comment containers, nested reply controls, and independently authored nested captions, rather than rejecting every nested article. Context metadata uses the same ownership rule. The model and backend were not changed for this correction.

The rebuilt unpacked extension passed a regression using a real locally served image in a nested article wrapper: **Check this image** appeared and caption-only preview was not selected automatically. Larger comment video and comment-link exclusion also passed. The 14 extension checks, product contract and build passed.

This verifies the reproduced structural layout, not the user's logged-in Facebook post. Reload SuriPH from `chrome-extension/dist`, confirm **1.3.20**, and refresh the Facebook tab before checking the original post again.
