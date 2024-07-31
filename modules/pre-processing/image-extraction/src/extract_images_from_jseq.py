"""
This python script will extract images from a pair of JSEQ + IDX file
Assumption: Input .jsq + .idx file with the same name
Please note we default to save as .jpg extension as it's the raw picture
"""

import os
import sys
import time


class JseqHandler:
    """JseqHandler Class"""

    def __init__(self, jsq_loc_in: str, idx_loc_in: str):
        """init"""
        self.jseq_file_location = jsq_loc_in
        self.idx_file_location = idx_loc_in
        self.jseq_file_reader = open(self.jseq_file_location, "rb")
        index_file_reader = open(self.idx_file_location, "rb")
        self.indexes = []
        index_location = index_file_reader.read(8)
        t0_init = time.time()
        while index_location != b"":
            index = int.from_bytes(index_location, byteorder="little", signed=False)
            self.indexes.append(index)
            index_location = index_file_reader.read(8)
        index_file_reader.close()
        t1_init = time.time()
        print(f"Elapsed time reading IDX File: {str(t1_init-t0_init)}")

    def get_frame(self, frame_id: int):
        """Get the individual frame"""
        t0_frame = time.time()
        start_read_location = self.indexes[frame_id]
        number_of_bytes_to_be_read = 0
        if frame_id + 1 == len(self.indexes):
            number_of_bytes_to_be_read = -1
        else:
            number_of_bytes_to_be_read = self.indexes[frame_id + 1] - self.indexes[frame_id]
        self.jseq_file_reader.seek(start_read_location, 0)
        output = self.jseq_file_reader.read(number_of_bytes_to_be_read)
        t1_frame = time.time()
        print(f"Elapsed time Single IDX File: {str(t1_frame-t0_frame)}")
        return output

    def __del__(self):
        self.jseq_file_reader.close()


if __name__ == "__main__":
    # Entry Point:
    # - the first argument is the location of the JSEQ + IDX file, they need to
    #  share the same name
    # - the second argument defines where the original files shall be located once
    #  processed so that we move them to another directory
    # - the third argument defines where the extracted images shall be stored
    mypath = sys.argv[1]
    processed = sys.argv[2]
    extracted = sys.argv[3]
    # start_range = sys.argv[4]
    # end_range = sys.argv[5]

    # List the files in the provided directory and looking for the .JSQ and .IDX file
    # We assume they have the same name
    for path in os.listdir(mypath):
        full_path_ext = os.path.join(mypath, path)

        # Only process each jsq / idx file pair once...
        if full_path_ext.endswith(".jsq"):
            print(f"Working on file {full_path_ext}")
            # Remove extension
            file_name = os.path.splitext(full_path_ext)[0]
            jsq_loc = file_name + ".jsq"
            idx_loc = file_name + ".idx"
            if os.path.isfile(jsq_loc) & os.path.isfile(idx_loc):
                # Instante the JSEQ class such that it would load the index of the frames
                jseq = JseqHandler(jsq_loc, idx_loc)

                # Iterate each frame and extract and save them as individual frames and save to .jpg
                print(f"-- About to start extracting {str(len(jseq.indexes) - 2)} images to {extracted}: ")
                t0 = time.time()

                # start_range = start_range if start_range else 0
                # end_range = end_range if end_range else int(len(jseq.indexes) - 2)

                start_range = 0
                end_range = int(len(jseq.indexes) - 2)

                if end_range > len(jseq.indexes) - 2 or end_range < start_range:
                    end_range = len(jseq.indexes) - 2
                    start_range = 0

                for idx in range(start_range, end_range):
                    print(f"-- Extracting frame with id {str(idx)}")
                    image_frame = jseq.get_frame(idx)
                    image_name = f"extract{str(idx)}"
                    with open(f"{extracted}{image_name}.jpg", "wb") as extractedImage:
                        extractedImage.write(image_frame)
                print(f"-- Just finished extracting with frame id: {str(idx)}")
                t1 = time.time()
                print(f"Elapsed time extracting all images File: {str(t1-t0)}")
        else:
            print(f"-- Skipping file {full_path_ext}")
